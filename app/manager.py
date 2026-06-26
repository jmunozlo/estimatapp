"""Scrum Poker room manager.

Delegates to the infrastructure repository for room storage.
Selects repository implementation based on ``REPOSITORY`` environment variable.
"""

import os
from uuid import uuid4

from app.domain import Room
from app.infrastructure import get_room_repository
from app.infrastructure.database.connection import get_pool
from app.infrastructure.repositories.postgres_room_repository import (
    PostgresRoomRepository,
)


class RoomManager:
    """Manages Scrum Poker rooms.

    Acts as an adapter between existing code and the repository interface.
    Selects ``InMemoryRoomRepository`` or ``PostgresRoomRepository`` based on
    the ``REPOSITORY`` environment variable ("inmemory" | "postgres").
    All methods are async to support the async RoomRepository contract.
    The pool connection is lazy — acquired on first use, not at init time.
    """

    def __init__(self) -> None:
        """Initialize the room manager.

        Reads ``REPOSITORY`` env var (default: "inmemory").
        Pool/connection is acquired lazily on first repository access.
        """
        self._repo_type = os.getenv("REPOSITORY", "inmemory").lower()
        self._repository = None  # lazy — initialized on first use

    def _get_repository(self):
        """Get or initialize the repository (lazy)."""
        if self._repository is not None:
            return self._repository

        if self._repo_type == "postgres":
            pool = get_pool()
            self._repository = PostgresRoomRepository(pool)
        else:
            self._repository = get_room_repository()
        return self._repository

    async def create_room(self, name: str) -> Room:
        """Create a new room."""
        room_id = str(uuid4())[:8]
        room = Room.create(room_id=room_id, name=name)
        await self._get_repository().save(room)
        return room

    async def get_room(self, room_id: str) -> Room | None:
        """Get a room by its ID."""
        return await self._get_repository().get_by_id(room_id)

    async def delete_room(self, room_id: str) -> None:
        """Delete a room."""
        return await self._get_repository().delete(room_id)

    async def list_rooms(self) -> list[Room]:
        """List all active rooms."""
        return await self._get_repository().list_all()

    async def count_rooms(self) -> int:
        """Count all rooms."""
        return await self._get_repository().count()


# Global room manager instance
room_manager = RoomManager()
