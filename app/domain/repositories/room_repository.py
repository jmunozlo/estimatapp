"""Room repository interface.

Defines the contract that all Room repository implementations must follow.
All methods are async to support both in-memory and PostgreSQL backends.
"""

from abc import ABC, abstractmethod

from app.domain.aggregates.room import Room


class RoomRepository(ABC):
    """Abstract interface for the room repository.

    Defines operations that any room repository implementation must provide.
    """

    @abstractmethod
    async def save(self, room: Room) -> None:
        """Save a room (create or update).

        Args:
            room: The room to save.
        """

    @abstractmethod
    async def get_by_id(self, room_id: str) -> Room | None:
        """Get a room by its ID.

        Args:
            room_id: The room identifier.

        Returns:
            The room if found, None otherwise.
        """

    @abstractmethod
    async def delete(self, room_id: str) -> bool:
        """Delete a room.

        Args:
            room_id: The identifier of the room to delete.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    async def list_all(self) -> list[Room]:
        """List all rooms.

        Returns:
            List of all existing rooms.
        """

    @abstractmethod
    async def exists(self, room_id: str) -> bool:
        """Check if a room exists.

        Args:
            room_id: The room identifier.

        Returns:
            True if the room exists.
        """

    @abstractmethod
    async def count(self) -> int:
        """Count the total number of rooms.

        Returns:
            Number of existing rooms.
        """

    @abstractmethod
    async def list_by_team(self, team_id: str) -> list[Room]:
        """List rooms belonging to a team.

        Args:
            team_id: The team identifier.

        Returns:
            List of rooms for the given team.
        """

    @abstractmethod
    async def count_by_team(self, team_id: str) -> int:
        """Count active rooms for a team (used for free tier limit enforcement).

        Args:
            team_id: The team identifier.

        Returns:
            Number of rooms belonging to the given team.
        """
