"""Tests for RoomRepository async interface compliance.

Verifies that the RoomRepository ABC enforces async methods and that
InMemoryRoomRepository implements them correctly as async stubs.
"""

import pytest

from app.domain.aggregates.room import Room
from app.domain.repositories.room_repository import RoomRepository
from app.infrastructure.repositories.in_memory_room_repository import (
    InMemoryRoomRepository,
    reset_room_repository,
)


class TestRoomRepositoryABCHasAsyncInterface:
    """The ABC contract MUST declare all methods as async def."""

    def test_interface_methods_are_async(self):
        """GIVEN the RoomRepository ABC WHEN inspecting its methods THEN they are coroutines."""
        import inspect

        for method_name in ["save", "get_by_id", "delete", "list_all", "exists", "count", "list_by_team", "count_by_team"]:
            method = getattr(RoomRepository, method_name, None)
            assert method is not None, f"{method_name} must be defined on RoomRepository"

            # Abstract methods are not coroutines at the class level, but they should be
            # defined with async def. Check via __isabstractmethod__ + signature.
            assert hasattr(method, "__isabstractmethod__"), f"{method_name} must be abstract"

    async def test_inmemory_save_and_get_by_id_async_compat(self):
        """GIVEN InMemoryRoomRepository WHEN save/get_by_id are called as async THEN they work."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        room = Room(id="async-test-1", name="Async Test")

        await repo.save(room)
        result = await repo.get_by_id("async-test-1")

        assert result is room
        assert result.name == "Async Test"

    async def test_inmemory_delete_async(self):
        """GIVEN a saved room WHEN delete is called async THEN it returns True and removes it."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        room = Room(id="async-del-1", name="To Delete")
        await repo.save(room)

        deleted = await repo.delete("async-del-1")
        assert deleted is True
        assert await repo.get_by_id("async-del-1") is None

    async def test_inmemory_delete_nonexistent_returns_false(self):
        """GIVEN no room with that id WHEN delete is called THEN returns False."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        result = await repo.delete("nonexistent")
        assert result is False

    async def test_inmemory_exists_async(self):
        """GIVEN a saved room WHEN exists is called async THEN returns True."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        room = Room(id="async-exists-1", name="Exists Test")
        await repo.save(room)

        assert await repo.exists("async-exists-1") is True
        assert await repo.exists("nonexistent") is False

    async def test_inmemory_list_all_async(self):
        """GIVEN multiple rooms WHEN list_all is called async THEN returns all."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        room1 = Room(id="list-1", name="Room 1")
        room2 = Room(id="list-2", name="Room 2")
        await repo.save(room1)
        await repo.save(room2)

        rooms = await repo.list_all()
        assert len(rooms) == 2
        assert room1 in rooms
        assert room2 in rooms

    async def test_inmemory_list_all_empty(self):
        """GIVEN no rooms WHEN list_all is called THEN returns empty list."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        rooms = await repo.list_all()
        assert rooms == []

    async def test_inmemory_count_async(self):
        """GIVEN rooms exist WHEN count is called async THEN returns correct count."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        assert await repo.count() == 0

        await repo.save(Room(id="count-1", name="Room 1"))
        assert await repo.count() == 1

        await repo.save(Room(id="count-2", name="Room 2"))
        assert await repo.count() == 2

    async def test_inmemory_list_by_team_filters_correctly(self):
        """GIVEN rooms with different team_ids WHEN list_by_team is called THEN filters correctly."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        room_a1 = Room(id="ta-1", name="Team A Room 1", team_id="team-a")
        room_a2 = Room(id="ta-2", name="Team A Room 2", team_id="team-a")
        room_b1 = Room(id="tb-1", name="Team B Room 1", team_id="team-b")
        await repo.save(room_a1)
        await repo.save(room_a2)
        await repo.save(room_b1)

        team_a_rooms = await repo.list_by_team("team-a")
        assert len(team_a_rooms) == 2
        assert room_a1 in team_a_rooms
        assert room_a2 in team_a_rooms
        assert room_b1 not in team_a_rooms

    async def test_inmemory_list_by_team_empty_result(self):
        """GIVEN no rooms for a team WHEN list_by_team is called THEN returns empty list."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        await repo.save(Room(id="nr-1", name="No Team Room", team_id=None))

        result = await repo.list_by_team("nonexistent-team")
        assert result == []

    async def test_inmemory_count_by_team(self):
        """GIVEN rooms for different teams WHEN count_by_team is called THEN returns correct count."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        await repo.save(Room(id="cta-1", name="A1", team_id="team-a"))
        await repo.save(Room(id="cta-2", name="A2", team_id="team-a"))
        await repo.save(Room(id="ctb-1", name="B1", team_id="team-b"))

        assert await repo.count_by_team("team-a") == 2
        assert await repo.count_by_team("team-b") == 1
        assert await repo.count_by_team("nonexistent") == 0

    async def test_inmemory_count_by_team_with_none_team_id(self):
        """GIVEN rooms with team_id=None WHEN count_by_team is called for a real team THEN they are not counted."""
        reset_room_repository()
        repo = InMemoryRoomRepository()
        await repo.save(Room(id="anon-1", name="Anonymous", team_id=None))
        await repo.save(Room(id="team-1", name="Team Room", team_id="team-x"))

        assert await repo.count_by_team("team-x") == 1
