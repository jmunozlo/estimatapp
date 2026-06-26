"""Tests for PostgresRoomRepository — mock-based, asyncpg pool mocked.

Covers save/get_by_id/delete/list_all/exists/list_by_team/count_by_team
with full aggregate round-trip and optimistic lock conflict detection.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.domain.aggregates.room import Room
from app.domain.entities.enums import RoomStatus, VotingMode
from app.domain.entities.player import Player
from app.domain.entities.story import StoryHistory

pytestmark = pytest.mark.asyncio


class MockRow:
    """Simulate an asyncpg row (dict-like with attribute-style access).

    Supports __contains__ so that ``"col" in row`` works.
    """

    def __init__(self, **kwargs):
        self._data = kwargs

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        return self._data.get(key, default)


def _room_row(room: Room, version: int = 1) -> MockRow:
    """Build a rooms table row mock from a Room aggregate."""
    return MockRow(
        id=room.id,
        name=room.name,
        team_id=room.team_id,
        created_by=room.created_by,
        status=room.status.value,
        voting_mode=room.voting_mode.value,
        voting_scale=room.voting_scale,
        custom_scale=str(room.custom_scale).replace("'", '"'),
        story_name=room.story_name or "",
        current_round=1,
        ended_at=room.ended_at,
        created_at=room.created_at,
        version=version,
    )


def _player_row(room_id: str, player: Player) -> MockRow:
    """Build a room_players row mock from a Player entity."""
    return MockRow(
        room_id=room_id,
        profile_id=player.id,
        display_name=player.name,
        is_observer=player.is_observer,
        is_facilitator=player.is_facilitator,
        connected=player.connected,
        joined_at=player.joined_at,
    )


def _vote_row(room_id: str, player: Player, round_number: int = 1) -> MockRow:
    """Build a votes row mock."""
    return MockRow(
        room_id=room_id,
        profile_id=player.id,
        round_number=round_number,
        vote_value=player.vote,
    )


def _story_row(story: StoryHistory, room_id: str) -> MockRow:
    """Build a stories row mock."""
    return MockRow(
        id="story-uuid",
        room_id=room_id,
        story_name=story.story_name,
        votes=story.votes,
        vote_summary=story.vote_summary,
        average=story.average,
        rounded_average=story.rounded_average,
        voted_at=story.voted_at,
        round_number=story.round_number,
        is_superseded=story.is_superseded,
    )


@pytest.fixture
def mock_conn():
    """Create a mocked asyncpg connection with common defaults."""
    conn = AsyncMock()
    # transaction() returns an async context manager synchronously
    conn.transaction = Mock(return_value=_TransactionContextManager(conn))
    # Default execute result so saves succeed
    conn.execute.return_value = "UPDATE 1"
    # Default fetchval returns 0 (no rows yet, etc.)
    conn.fetchval.return_value = 0
    return conn


class _AcquireContextManager:
    """Simulates asyncpg.Pool.acquire() async context manager.

    asyncpg.Pool.acquire() returns an async context manager synchronously
    (not a coroutine). The __aenter__ awaits and returns the connection.
    """

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


class _TransactionContextManager:
    """Simulates asyncpg.Connection.transaction() async context manager.

    connection.transaction() returns an async context manager synchronously.
    """

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_pool(mock_conn):
    """Create a mocked asyncpg Pool that returns mock_conn via acquire()."""
    pool = Mock(spec=["acquire"])
    pool.acquire = Mock(return_value=_AcquireContextManager(mock_conn))
    pool.acquire.return_value = _AcquireContextManager(mock_conn)
    return pool


@pytest.fixture
def repo(mock_pool):
    """Create a PostgresRoomRepository with mocked pool."""
    from app.infrastructure.repositories.postgres_room_repository import (
        PostgresRoomRepository,
    )

    return PostgresRoomRepository(mock_pool)


@pytest.fixture
def sample_room() -> Room:
    """A room with 3 players, 2 votes, and 1 story."""
    room = Room(
        id="room-abc",
        name="Sprint 42",
        team_id="team-uuid-1",
        created_by="user-uuid-1",
    )
    room.add_player(Player(id="p1", name="Alice", is_facilitator=True))
    room.add_player(Player(id="p2", name="Bob", is_observer=False))
    room.add_player(Player(id="p3", name="Observer", is_observer=True))
    room.players["p1"].vote = "5"
    room.players["p2"].vote = "8"

    story = StoryHistory(
        story_name="US-001 Login",
        votes={"Alice": "5", "Bob": "8"},
        vote_summary={"5": 1, "8": 1},
        average=6.5,
        rounded_average="8",
        round_number=1,
        is_superseded=False,
    )
    room.history.append(story)
    room.story_name = "US-002 Logout"
    return room


class TestPostgresRoomRepositorySave:
    """PostgresRoomRepository.save() behavior."""

    async def test_save_inserts_new_room(self, repo, mock_pool, mock_conn, sample_room):
        """GIVEN a new room WHEN save is called THEN it INSERTs room + players + votes."""
        mock_conn.fetchrow.return_value = None  # Room does not exist yet
        mock_conn.execute.return_value = "INSERT 1"

        await repo.save(sample_room)

        # Should have called execute for room upsert
        room_calls = [
            c for c in mock_conn.execute.call_args_list if "INSERT INTO rooms" in str(c)
        ]
        assert len(room_calls) >= 1, "Expected INSERT INTO rooms to be called"

    async def test_save_updates_existing_room(self, repo, mock_pool, mock_conn, sample_room):
        """GIVEN an existing room WHEN save is called THEN it UPDATEs with version check."""
        # First load returns a version, then save checks it
        mock_conn.fetchrow.side_effect = [
            _room_row(sample_room, version=1),  # First call in get_by_id
            None,  # No existing row for the save check
        ]
        repo_version_data: dict = {}
        repo_version_data[sample_room.id] = 1

        await repo.save(sample_room)

        room_update_calls = [
            c for c in mock_conn.execute.call_args_list
            if "version" in str(c).lower()
        ]
        assert len(room_update_calls) >= 1

    async def test_save_raises_on_optimistic_lock_conflict(
        self, repo, mock_pool, mock_conn, sample_room
    ):
        """GIVEN a version mismatch WHEN save is called THEN it raises OptimisticLockError."""
        from app.infrastructure.repositories.postgres_room_repository import (
            OptimisticLockError,
        )

        # Return version=2 so save enters the UPDATE path
        mock_conn.fetchrow.return_value = _room_row(sample_room, version=2)
        # Make the UPDATE fail (no rows matched) — version conflict
        mock_conn.execute.return_value = "UPDATE 0"

        with pytest.raises(OptimisticLockError):
            await repo.save(sample_room)

    async def test_save_persists_players(self, repo, mock_pool, mock_conn, sample_room):
        """GIVEN a room with players WHEN save is called THEN DELETE + INSERT room_players runs."""
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"

        await repo.save(sample_room)

        delete_player_calls = [
            c for c in mock_conn.execute.call_args_list
            if "DELETE FROM room_players" in str(c)
        ]
        assert len(delete_player_calls) == 1

        insert_player_calls = [
            c for c in mock_conn.execute.call_args_list
            if "INSERT INTO room_players" in str(c)
        ]
        assert len(insert_player_calls) == 3

    async def test_save_persists_votes(self, repo, mock_pool, mock_conn, sample_room):
        """GIVEN players with votes WHEN save is called THEN votes are upserted."""
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"

        await repo.save(sample_room)

        vote_calls = [
            c for c in mock_conn.execute.call_args_list
            if "INSERT INTO votes" in str(c)
        ]
        # Two players with votes (Alice=5, Bob=8)
        assert len(vote_calls) == 2

    async def test_save_persists_stories(self, repo, mock_pool, mock_conn, sample_room):
        """GIVEN a room with story history WHEN save is called THEN stories are inserted."""
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"

        await repo.save(sample_room)

        story_calls = [
            c for c in mock_conn.execute.call_args_list
            if "INSERT INTO stories" in str(c)
        ]
        assert len(story_calls) == 1

    async def test_save_runs_in_transaction(self, repo, mock_pool, mock_conn, sample_room):
        """GIVEN save is called THEN it runs inside a transaction."""
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"

        await repo.save(sample_room)

        mock_conn.transaction.assert_called_once()


class TestPostgresRoomRepositoryGetById:
    """PostgresRoomRepository.get_by_id() behavior."""

    async def test_get_by_id_returns_full_aggregate(
        self, repo, mock_pool, mock_conn, sample_room
    ):
        """GIVEN an existing room WHEN get_by_id is called THEN the full aggregate is returned."""
        mock_conn.fetchrow.return_value = _room_row(sample_room, version=1)
        mock_conn.fetch.side_effect = [
            [_player_row("room-abc", p) for p in sample_room.players.values()],
            [],  # No votes for current round (not in sample_room context)
            [],  # No votes for current round (separate call)
            [_story_row(story, "room-abc") for story in sample_room.history],
        ]

        result = await repo.get_by_id("room-abc")

        assert result is not None
        assert result.id == "room-abc"
        assert result.name == "Sprint 42"
        assert result.team_id == "team-uuid-1"
        assert len(result.players) == 3
        assert result.history is not None

    async def test_get_by_id_returns_none_for_missing(
        self, repo, mock_pool, mock_conn
    ):
        """GIVEN a nonexistent room_id WHEN get_by_id is called THEN returns None."""
        mock_conn.fetchrow.return_value = None

        result = await repo.get_by_id("nonexistent")
        assert result is None

    async def test_get_by_id_loads_player_votes(
        self, repo, mock_pool, mock_conn, sample_room
    ):
        """GIVEN players with votes WHEN get_by_id is called THEN player.vote is set."""
        mock_conn.fetchrow.return_value = _room_row(sample_room, version=1)
        mock_conn.fetch.side_effect = [
            [_player_row("room-abc", p) for p in sample_room.players.values()],
            [
                _vote_row("room-abc", sample_room.players["p1"]),
                _vote_row("room-abc", sample_room.players["p2"]),
            ],
            [_story_row(story, "room-abc") for story in sample_room.history],
        ]

        result = await repo.get_by_id("room-abc")

        assert result is not None
        p1 = result.get_player("p1")
        assert p1 is not None
        assert p1.vote == "5"
        p2 = result.get_player("p2")
        assert p2 is not None
        assert p2.vote == "8"


class TestPostgresRoomRepositoryDelete:
    """PostgresRoomRepository.delete() behavior."""

    async def test_delete_existing_room(self, repo, mock_pool, mock_conn):
        """GIVEN an existing room WHEN delete is called THEN it DELETE FROM rooms."""
        mock_conn.execute.return_value = "DELETE 1"

        result = await repo.delete("room-abc")
        assert result is True

    async def test_delete_nonexistent_room(self, repo, mock_pool, mock_conn):
        """GIVEN a nonexistent room WHEN delete is called THEN returns False."""
        mock_conn.execute.return_value = "DELETE 0"

        result = await repo.delete("nonexistent")
        assert result is False


class TestPostgresRoomRepositoryListAll:
    """PostgresRoomRepository.list_all() behavior."""

    async def test_list_all_returns_rooms(
        self, repo, mock_pool, mock_conn, sample_room
    ):
        """GIVEN rooms exist WHEN list_all is called THEN returns all."""
        mock_conn.fetch.return_value = [
            _room_row(sample_room, version=1),
        ]

        results = await repo.list_all()
        assert len(results) == 1

    async def test_list_all_empty(self, repo, mock_pool, mock_conn):
        """GIVEN no rooms WHEN list_all is called THEN returns empty list."""
        mock_conn.fetch.return_value = []

        results = await repo.list_all()
        assert results == []


class TestPostgresRoomRepositoryExists:
    """PostgresRoomRepository.exists() behavior."""

    async def test_exists_returns_true(self, repo, mock_pool, mock_conn):
        """GIVEN an existing room WHEN exists is called THEN returns True."""
        mock_conn.fetchval.return_value = 1

        assert await repo.exists("room-abc") is True

    async def test_exists_returns_false(self, repo, mock_pool, mock_conn):
        """GIVEN a nonexistent room WHEN exists is called THEN returns False."""
        mock_conn.fetchval.return_value = None

        assert await repo.exists("nonexistent") is False


class TestPostgresRoomRepositoryCount:
    """PostgresRoomRepository.count() behavior."""

    async def test_count_returns_number(self, repo, mock_pool, mock_conn):
        """GIVEN rooms in DB WHEN count is called THEN returns the count."""
        mock_conn.fetchval.return_value = 5

        assert await repo.count() == 5


class TestPostgresRoomRepositoryListByTeam:
    """PostgresRoomRepository.list_by_team() behavior."""

    async def test_list_by_team_filters_correctly(
        self, repo, mock_pool, mock_conn, sample_room
    ):
        """GIVEN rooms for a team WHEN list_by_team is called THEN returns only those."""
        mock_conn.fetch.return_value = [_room_row(sample_room, version=1)]

        results = await repo.list_by_team("team-uuid-1")
        assert len(results) == 1


class TestPostgresRoomRepositoryCountByTeam:
    """PostgresRoomRepository.count_by_team() behavior."""

    async def test_count_by_team_returns_count(self, repo, mock_pool, mock_conn):
        """GIVEN rooms for a team WHEN count_by_team is called THEN returns correct count."""
        mock_conn.fetchval.return_value = 3

        assert await repo.count_by_team("team-uuid-1") == 3
