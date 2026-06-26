"""In-memory implementation of the room repository."""

from app.domain.aggregates import Room
from app.domain.repositories import RoomRepository


class InMemoryRoomRepository(RoomRepository):
    """In-memory implementation of the room repository.

    Stores rooms in a dictionary. Useful for development and testing.
    All methods are async stubs that complete immediately (no I/O).
    """

    _instance: "InMemoryRoomRepository | None" = None

    def __new__(cls) -> "InMemoryRoomRepository":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rooms = {}
        return cls._instance

    def __init__(self) -> None:
        """Initialize the repository (first time only)."""

    async def save(self, room: Room) -> None:
        """Save a room (create or update)."""
        self._rooms[room.id] = room

    async def get_by_id(self, room_id: str) -> Room | None:
        """Get a room by its ID."""
        return self._rooms.get(room_id)

    async def delete(self, room_id: str) -> bool:
        """Delete a room.

        Returns:
            True if deleted, False if not found.
        """
        if room_id in self._rooms:
            del self._rooms[room_id]
            return True
        return False

    async def list_all(self) -> list[Room]:
        """List all rooms."""
        return list(self._rooms.values())

    async def exists(self, room_id: str) -> bool:
        """Check if a room exists."""
        return room_id in self._rooms

    async def count(self) -> int:
        """Count the total number of rooms."""
        return len(self._rooms)

    async def list_by_team(self, team_id: str) -> list[Room]:
        """List rooms belonging to a team.

        Args:
            team_id: The team identifier.

        Returns:
            List of rooms with matching team_id.
        """
        return [room for room in self._rooms.values() if room.team_id == team_id]

    async def count_by_team(self, team_id: str) -> int:
        """Count rooms for a team.

        Args:
            team_id: The team identifier.

        Returns:
            Number of rooms belonging to the given team.
        """
        return sum(1 for room in self._rooms.values() if room.team_id == team_id)

    def clear(self) -> None:
        """Clear all rooms (useful for testing)."""
        self._rooms.clear()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for tests)."""
        if cls._instance is not None:
            cls._instance._rooms.clear()


def get_room_repository() -> InMemoryRoomRepository:
    """Get the room repository singleton instance."""
    return InMemoryRoomRepository()


def reset_room_repository() -> None:
    """Reset the repository (useful for tests)."""
    InMemoryRoomRepository.reset_instance()
