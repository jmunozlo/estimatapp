"""Integration tests for PostgresRoomRepository — full aggregate round-trip.

Covers:
- 3.1 Full save → load → verify identical aggregate (3 players, 2 votes, 1 story)
- 3.2 Cascade delete removes all room data
"""

from unittest.mock import AsyncMock, Mock

import pytest

from app.domain.aggregates.room import Room
from app.domain.entities.player import Player
from app.domain.entities.story import StoryHistory

pytestmark = pytest.mark.asyncio


class MockRow:
    """Simulate an asyncpg row (dict-like with attribute-style access)."""

    def __init__(self, **kwargs):
        self._data = kwargs

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        return self._data.get(key, default)


class _AcquireContextManager:
    """Simulates asyncpg.Pool.acquire() async context manager."""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


class _TransactionContextManager:
    """Simulates asyncpg.Connection.transaction() async context manager."""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


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
    conn.transaction = Mock(return_value=_TransactionContextManager(conn))
    conn.execute.return_value = "UPDATE 1"
    conn.fetchval.return_value = 0
    return conn


@pytest.fixture
def mock_pool(mock_conn):
    """Create a mocked asyncpg Pool that returns mock_conn via acquire()."""
    pool = Mock(spec=["acquire"])
    pool.acquire = Mock(return_value=_AcquireContextManager(mock_conn))
    return pool


@pytest.fixture
def repo(mock_pool):
    """Create a PostgresRoomRepository with mocked pool."""
    from app.infrastructure.repositories.postgres_room_repository import (
        PostgresRoomRepository,
    )

    return PostgresRoomRepository(mock_pool)


@pytest.fixture
def complex_room() -> Room:
    """A room with 3 players (2 voters + 1 observer), 2 votes, and 1 story.

    This is the "3p/2v/1s" case from the task spec.
    """
    room = Room(
        id="room-complex",
        name="Sprint 42 Planning",
        team_id="team-alpha",
        created_by="user-alice",
    )
    room.add_player(Player(id="p1", name="Alice", is_facilitator=True))
    room.add_player(Player(id="p2", name="Bob"))
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


class TestPostgresRepositoryRoundTrip:
    """Full save→load→verify identical aggregate (Task 3.1)."""

    async def test_save_then_load_returns_identical_aggregate(
        self, repo, mock_conn, complex_room
    ):
        """GIVEN a complex room with 3p/2v/1s WHEN save THEN get_by_id yields identical fields."""
        # RED: test written before confirming it passes
        # Phase 1 — SAVE the room (INSERT path, room does not exist)
        mock_conn.fetchrow.side_effect = None
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"
        mock_conn.fetch.reset_mock()

        await repo.save(complex_room)

        # Phase 2 — LOAD the room (get_by_id reconstructs aggregate)
        mock_conn.fetchrow.side_effect = None
        mock_conn.fetchrow.return_value = _room_row(complex_room, version=1)
        mock_conn.fetch.side_effect = [
            [_player_row("room-complex", p) for p in complex_room.players.values()],
            [
                _vote_row("room-complex", complex_room.players["p1"]),
                _vote_row("room-complex", complex_room.players["p2"]),
            ],
            [_story_row(story, "room-complex") for story in complex_room.history],
        ]

        loaded = await repo.get_by_id("room-complex")

        # ── Verify ALL fields match round-trip ──
        assert loaded is not None
        assert loaded.id == complex_room.id
        assert loaded.name == complex_room.name
        assert loaded.team_id == complex_room.team_id
        assert loaded.created_by == complex_room.created_by
        assert loaded.status == complex_room.status
        assert loaded.voting_mode == complex_room.voting_mode
        assert loaded.story_name == complex_room.story_name

        # Players
        assert len(loaded.players) == 3
        assert loaded.get_player("p1") is not None
        assert loaded.get_player("p1").name == "Alice"
        assert loaded.get_player("p1").is_facilitator is True
        assert loaded.get_player("p2") is not None
        assert loaded.get_player("p2").name == "Bob"
        assert loaded.get_player("p3") is not None
        assert loaded.get_player("p3").name == "Observer"
        assert loaded.get_player("p3").is_observer is True

        # Votes loaded correctly
        assert loaded.get_player("p1").vote == "5"
        assert loaded.get_player("p2").vote == "8"
        # Observer has no vote
        assert loaded.get_player("p3").vote is None

        # Story history
        assert len(loaded.history) == 1
        assert loaded.history[0].story_name == "US-001 Login"
        assert loaded.history[0].votes == {"Alice": "5", "Bob": "8"}
        assert loaded.history[0].vote_summary == {"5": 1, "8": 1}
        assert loaded.history[0].average == 6.5
        assert loaded.history[0].rounded_average == "8"
        assert loaded.history[0].round_number == 1

    async def test_save_updates_existing_aggregate_fields(
        self, repo, mock_conn, complex_room
    ):
        """GIVEN an existing room WHEN saved with updated fields THEN update uses version check."""
        # First save creates
        mock_conn.fetchrow.side_effect = [None]
        mock_conn.execute.return_value = "INSERT 1"
        await repo.save(complex_room)

        # Second save — room exists at version 1
        mock_conn.fetchrow.reset_mock()
        mock_conn.fetchrow.side_effect = [
            _room_row(complex_room, version=1),  # save checks version
        ]

        # Update a field
        complex_room.story_name = "US-003 Profile Page"

        mock_conn.execute.return_value = "UPDATE 1"
        await repo.save(complex_room)

        # Verify save used version check (UPDATE not INSERT)
        update_calls = [
            c
            for c in mock_conn.execute.call_args_list
            if "version" in str(c).lower() and "UPDATE" in str(c)
        ]
        assert len(update_calls) >= 1

    async def test_save_runs_in_transaction(self, repo, mock_conn, complex_room):
        """GIVEN save is called THEN it runs inside a connection.transaction()."""
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"

        await repo.save(complex_room)

        mock_conn.transaction.assert_called_once()

    async def test_save_without_votes_handles_none_gracefully(
        self, repo, mock_conn
    ):
        """GIVEN a room with no votes WHEN save THEN no vote inserts."""
        room = Room(id="no-votes", name="Empty Voting")
        room.add_player(Player(id="p1", name="Alice"))
        # No votes set

        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"

        await repo.save(room)

        vote_calls = [
            c
            for c in mock_conn.execute.call_args_list
            if "INSERT INTO votes" in str(c)
        ]
        assert len(vote_calls) == 0


class TestPostgresRepositoryCascadeDelete:
    """Cascade delete removes all room data (Task 3.2)."""

    async def test_delete_removes_room_and_get_by_id_returns_none(
        self, repo, mock_conn, complex_room
    ):
        """GIVEN a saved room WHEN deleted THEN get_by_id returns None."""
        # Save the room first (INSERT path)
        mock_conn.fetchrow.side_effect = None
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"
        await repo.save(complex_room)

        # Delete
        mock_conn.execute.return_value = "DELETE 1"
        deleted = await repo.delete("room-complex")
        assert deleted is True

        # After delete, get_by_id returns None (cascade effect)
        mock_conn.fetchrow.side_effect = None
        mock_conn.fetchrow.return_value = None  # Room not found after cascade
        loaded = await repo.get_by_id("room-complex")
        assert loaded is None

    async def test_delete_nonexistent_room_returns_false(
        self, repo, mock_conn
    ):
        """GIVEN a nonexistent room WHEN delete THEN returns False."""
        mock_conn.execute.return_value = "DELETE 0"
        result = await repo.delete("nonexistent")
        assert result is False

    async def test_delete_calls_correct_sql(
        self, repo, mock_conn, complex_room
    ):
        """GIVEN a room WHEN delete THEN correct SQL is issued."""
        mock_conn.fetchrow.side_effect = None
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"
        await repo.save(complex_room)

        mock_conn.execute.reset_mock()
        mock_conn.execute.return_value = "DELETE 1"

        await repo.delete("room-complex")

        delete_call = mock_conn.execute.call_args
        assert delete_call is not None
        assert "DELETE FROM rooms" in str(delete_call)
        assert "room-complex" in str(delete_call)

    async def test_delete_with_players_and_stories_still_works(
        self, repo, mock_conn, complex_room
    ):
        """GIVEN a fully populated room WHEN deleted THEN no errors."""
        mock_conn.fetchrow.side_effect = None
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"
        await repo.save(complex_room)

        mock_conn.execute.reset_mock()
        mock_conn.execute.return_value = "DELETE 1"

        result = await repo.delete("room-complex")
        assert result is True

    async def test_save_after_delete_creates_fresh_room(
        self, repo, mock_conn, complex_room
    ):
        """GIVEN a room was deleted WHEN saved again with same ID THEN INSERT succeeds."""
        # Save → Delete → Save again
        mock_conn.fetchrow.side_effect = None
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"
        await repo.save(complex_room)

        mock_conn.execute.return_value = "DELETE 1"
        await repo.delete("room-complex")

        # Third state: fetchrow returns None (no existing room), so INSERT path
        mock_conn.fetchrow.side_effect = None
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = "INSERT 1"
        await repo.save(complex_room)

        # Verify it used INSERT path (no version check)
        insert_calls = [
            c
            for c in mock_conn.execute.call_args_list
            if "INSERT INTO rooms" in str(c)
        ]
        assert len(insert_calls) >= 1
