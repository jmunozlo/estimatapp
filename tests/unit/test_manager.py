"""Tests for RoomManager (async interface)."""

import pytest

from app.manager import RoomManager


pytestmark = pytest.mark.asyncio


class TestRoomManager:
    """Tests for the RoomManager class."""

    async def test_create_room(self, fresh_room_manager: RoomManager):
        """Verify that a room can be created."""
        room = await fresh_room_manager.create_room("Sprint Planning")

        assert room.name == "Sprint Planning"
        assert room.id is not None
        assert len(room.id) == 8

    async def test_create_room_generates_unique_ids(self, fresh_room_manager: RoomManager):
        """Verify that each room has a unique ID."""
        room1 = await fresh_room_manager.create_room("Room 1")
        room2 = await fresh_room_manager.create_room("Room 2")

        assert room1.id != room2.id

    async def test_create_room_stores_in_repo(self, fresh_room_manager: RoomManager):
        """Verify that the room is stored correctly."""
        room = await fresh_room_manager.create_room("Test Room")

        rooms = await fresh_room_manager.list_rooms()
        assert room in rooms

    async def test_get_room_returns_existing_room(self, fresh_room_manager: RoomManager):
        """Verify that an existing room can be retrieved."""
        created = await fresh_room_manager.create_room("Test")

        retrieved = await fresh_room_manager.get_room(created.id)

        assert retrieved is created

    async def test_get_room_returns_none_for_nonexistent(self, fresh_room_manager: RoomManager):
        """Verify that None is returned for a nonexistent room."""
        assert await fresh_room_manager.get_room("nonexistent") is None

    async def test_delete_room(self, fresh_room_manager: RoomManager):
        """Verify that a room can be deleted."""
        room = await fresh_room_manager.create_room("To Delete")

        await fresh_room_manager.delete_room(room.id)

        assert await fresh_room_manager.get_room(room.id) is None

    async def test_delete_nonexistent_room_does_not_raise(self, fresh_room_manager: RoomManager):
        """Verify that deleting a nonexistent room does not raise."""
        await fresh_room_manager.delete_room("nonexistent")  # Should not raise

    async def test_list_rooms_returns_all_rooms(self, fresh_room_manager: RoomManager):
        """Verify that list_rooms returns all rooms."""
        room1 = await fresh_room_manager.create_room("Room 1")
        room2 = await fresh_room_manager.create_room("Room 2")
        room3 = await fresh_room_manager.create_room("Room 3")

        rooms = await fresh_room_manager.list_rooms()

        assert len(rooms) == 3
        assert room1 in rooms
        assert room2 in rooms
        assert room3 in rooms

    async def test_list_rooms_returns_empty_when_no_rooms(self, fresh_room_manager: RoomManager):
        """Verify that list_rooms returns an empty list when no rooms exist."""
        rooms = await fresh_room_manager.list_rooms()

        assert rooms == []

    async def test_count_rooms(self, fresh_room_manager: RoomManager):
        """Verify count returns correct number."""
        assert await fresh_room_manager.count_rooms() == 0
        await fresh_room_manager.create_room("Room 1")
        assert await fresh_room_manager.count_rooms() == 1
        await fresh_room_manager.create_room("Room 2")
        assert await fresh_room_manager.count_rooms() == 2

    async def test_multiple_operations(self, fresh_room_manager: RoomManager):
        """Verify multiple operations in sequence."""
        room1 = await fresh_room_manager.create_room("Room 1")
        room2 = await fresh_room_manager.create_room("Room 2")
        assert len(await fresh_room_manager.list_rooms()) == 2

        await fresh_room_manager.delete_room(room1.id)
        assert len(await fresh_room_manager.list_rooms()) == 1

        assert await fresh_room_manager.get_room(room1.id) is None
        assert await fresh_room_manager.get_room(room2.id) is room2
