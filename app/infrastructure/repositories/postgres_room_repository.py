"""PostgreSQL implementation of the RoomRepository ABC.

Uses asyncpg connection pool for all operations. Implements full aggregate
save/load with transactional consistency and optimistic locking.
"""

import json

import asyncpg

from app.domain.aggregates.room import Room
from app.domain.entities.enums import RoomStatus, VotingMode
from app.domain.entities.player import Player
from app.domain.entities.story import StoryHistory
from app.domain.repositories.room_repository import RoomRepository


class OptimisticLockError(Exception):
    """Raised when a concurrent save detects a version mismatch."""


def _try_parse_json(value: str | bytes | None) -> list:
    """Safely parse a JSON string, returning [] on null or empty input."""
    if not value:
        return []
    try:
        return json.loads(value) if isinstance(value, (str, bytes)) else value
    except (json.JSONDecodeError, TypeError):
        return []


def _build_room_from_row(row: asyncpg.Record) -> Room:
    """Build a Room aggregate from a rooms table row."""
    return Room(
        id=row["id"],
        name=row["name"],
        team_id=row.get("team_id"),
        created_by=row.get("created_by"),
        status=RoomStatus(row.get("status", "voting")),
        voting_mode=VotingMode(row.get("voting_mode", "public")),
        voting_scale=row.get("voting_scale", "modified_fibonacci"),
        custom_scale=_try_parse_json(row.get("custom_scale")),
        story_name=row.get("story_name", "") or "",
        created_at=row.get("created_at"),
        ended_at=row.get("ended_at"),
    )


def _get_current_round(conn_record: asyncpg.Record | None, room_id: str) -> int:
    """Get the current round number from the room record, defaulting to 1."""
    if conn_record and "current_round" in conn_record:
        return conn_record["current_round"] or 1
    return 1


class PostgresRoomRepository(RoomRepository):
    """PostgreSQL implementation of RoomRepository using asyncpg pool.

    Stores the full Room aggregate (room + players + votes + stories)
    in a single database transaction. Optimistic locking via version column.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Initialize with an asyncpg connection pool.

        Args:
            pool: Initialized asyncpg connection pool.
        """
        self._pool = pool

    async def save(self, room: Room) -> None:
        """Save a room (create or update) with optimistic locking.

        Full aggregate save in a single transaction.
        Raises OptimisticLockError if version check fails.
        """
        async with self._pool.acquire() as conn, conn.transaction():
                # Read current version from DB for optimistic lock
                existing = await conn.fetchrow(
                    "SELECT version FROM rooms WHERE id = $1", room.id
                )

                if existing is not None:
                    expected_version = existing["version"]
                    # Try update with version check
                    result = await conn.execute(
                        """
                        UPDATE rooms
                        SET name = $2, team_id = $3, created_by = $4,
                            status = $5, voting_mode = $6, voting_scale = $7,
                            custom_scale = $8, story_name = $9, ended_at = $10,
                            current_round = $11, version = version + 1
                        WHERE id = $1 AND version = $12
                        """,
                        room.id,
                        room.name,
                        room.team_id,
                        room.created_by,
                        room.status.value,
                        room.voting_mode.value,
                        room.voting_scale,
                        json.dumps(room.custom_scale),
                        room.story_name or "",
                        room.ended_at,
                        _get_current_round(existing, room.id),
                        expected_version,
                    )

                    if result == "UPDATE 0":
                        raise OptimisticLockError(
                            f"Room '{room.id}' was modified by another request. "
                            f"Expected version {expected_version}."
                        )
                else:
                    # New room — INSERT
                    await conn.execute(
                        """
                        INSERT INTO rooms
                            (id, name, team_id, created_by, status,
                             voting_mode, voting_scale, custom_scale,
                             story_name, ended_at, version)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        """,
                        room.id,
                        room.name,
                        room.team_id,
                        room.created_by,
                        room.status.value,
                        room.voting_mode.value,
                        room.voting_scale,
                        json.dumps(room.custom_scale),
                        room.story_name or "",
                        room.ended_at,
                        1,
                    )

                # Save players (delete + insert)
                await conn.execute(
                    "DELETE FROM room_players WHERE room_id = $1", room.id
                )
                for player in room.players.values():
                    await conn.execute(
                        """
                        INSERT INTO room_players
                            (room_id, profile_id, display_name,
                             is_observer, is_facilitator, connected, joined_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        room.id,
                        player.id,
                        player.name,
                        player.is_observer,
                        player.is_facilitator,
                        player.connected,
                        player.joined_at,
                    )

                # Save current round votes
                current_round = _get_current_round(existing, room.id)
                for player in room.players.values():
                    if player.vote is not None:
                        await conn.execute(
                            """
                            INSERT INTO votes
                                (room_id, profile_id, round_number, vote_value)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (room_id, profile_id, round_number)
                            DO UPDATE SET vote_value = EXCLUDED.vote_value
                            """,
                            room.id,
                            player.id,
                            current_round,
                            player.vote,
                        )

                # Save story history (new entries only)
                existing_story_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM stories WHERE room_id = $1", room.id
                )
                new_stories = room.history[existing_story_count:] if existing_story_count else room.history
                for story in new_stories:
                    await conn.execute(
                        """
                        INSERT INTO stories
                            (room_id, story_name, votes, vote_summary,
                             average, rounded_average, voted_at,
                             round_number, is_superseded)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        room.id,
                        story.story_name,
                        json.dumps(story.votes),
                        json.dumps(story.vote_summary),
                        story.average,
                        story.rounded_average,
                        story.voted_at,
                        story.round_number,
                        story.is_superseded,
                    )

    async def get_by_id(self, room_id: str) -> Room | None:
        """Get a room by its ID with full aggregate reconstruction.

        Returns:
            Fully reconstructed Room aggregate with players, votes, and stories,
            or None if the room does not exist.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM rooms WHERE id = $1", room_id)
            if not row:
                return None

            room = _build_room_from_row(row)

            # Load players
            player_rows = await conn.fetch(
                "SELECT * FROM room_players WHERE room_id = $1", room_id
            )
            for pr in player_rows:
                player = Player(
                    id=pr["profile_id"],
                    name=pr["display_name"],
                    is_observer=pr["is_observer"],
                    is_facilitator=pr["is_facilitator"],
                    connected=pr["connected"],
                    joined_at=pr["joined_at"],
                )
                room.add_player(player)

            # Load current round votes
            current_round = _get_current_round(row, room_id)
            vote_rows = await conn.fetch(
                """
                SELECT * FROM votes
                WHERE room_id = $1 AND round_number = $2
                """,
                room_id,
                current_round,
            )
            for vr in vote_rows:
                player = room.get_player(vr["profile_id"])
                if player:
                    player.vote = vr["vote_value"]

            # Load story history
            story_rows = await conn.fetch(
                "SELECT * FROM stories WHERE room_id = $1 ORDER BY voted_at",
                room_id,
            )
            for sr in story_rows:
                room.history.append(
                    StoryHistory(
                        story_name=sr["story_name"],
                        votes=_try_parse_json(sr.get("votes")),
                        vote_summary=_try_parse_json(sr.get("vote_summary")),
                        average=sr["average"],
                        rounded_average=str(sr["rounded_average"]) if sr["rounded_average"] is not None else None,
                        voted_at=sr["voted_at"],
                        round_number=sr["round_number"],
                        is_superseded=sr["is_superseded"],
                    )
                )

            return room

    async def delete(self, room_id: str) -> bool:
        """Delete a room (cascade handled by DB).

        Returns:
            True if deleted, False if not found.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM rooms WHERE id = $1", room_id)
            return "DELETE 1" in result

    async def list_all(self) -> list[Room]:
        """List all rooms (basic info, no players/votes)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM rooms ORDER BY created_at DESC"
            )
            return [_build_room_from_row(r) for r in rows]

    async def exists(self, room_id: str) -> bool:
        """Check if a room exists."""
        async with self._pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT 1 FROM rooms WHERE id = $1", room_id
            )
            return val is not None

    async def count(self) -> int:
        """Count the total number of rooms."""
        async with self._pool.acquire() as conn:
            val = await conn.fetchval("SELECT COUNT(*) FROM rooms")
            return val or 0

    async def list_by_team(self, team_id: str) -> list[Room]:
        """List rooms belonging to a team."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM rooms WHERE team_id = $1 ORDER BY created_at DESC",
                team_id,
            )
            return [_build_room_from_row(r) for r in rows]

    async def count_by_team(self, team_id: str) -> int:
        """Count rooms for a team."""
        async with self._pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COUNT(*) FROM rooms WHERE team_id = $1", team_id
            )
            return val or 0
