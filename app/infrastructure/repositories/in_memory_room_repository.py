"""Implementación en memoria del repositorio de salas."""

from app.domain.aggregates import Room
from app.domain.repositories import RoomRepository


class InMemoryRoomRepository(RoomRepository):
    """Implementación en memoria del repositorio de salas.

    Esta implementación almacena las salas en un diccionario en memoria.
    Es útil para desarrollo y testing.
    """

    _instance: "InMemoryRoomRepository | None" = None

    def __new__(cls) -> "InMemoryRoomRepository":
        """Implementa el patrón Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rooms = {}
        return cls._instance

    def __init__(self) -> None:
        """Inicializa el repositorio (solo la primera vez)."""
        # _rooms se inicializa en __new__

    def save(self, room: Room) -> None:
        """Guarda una sala (crear o actualizar).

        Args:
            room: La sala a guardar.
        """
        self._rooms[room.id] = room

    def get_by_id(self, room_id: str) -> Room | None:
        """Obtiene una sala por su ID.

        Args:
            room_id: El identificador de la sala.

        Returns:
            La sala si existe, None en caso contrario.
        """
        return self._rooms.get(room_id)

    def delete(self, room_id: str) -> bool:
        """Elimina una sala.

        Args:
            room_id: El identificador de la sala a eliminar.

        Returns:
            True si se eliminó, False si no existía.
        """
        if room_id in self._rooms:
            del self._rooms[room_id]
            return True
        return False

    def list_all(self) -> list[Room]:
        """Lista todas las salas.

        Returns:
            Lista de todas las salas existentes.
        """
        return list(self._rooms.values())

    def exists(self, room_id: str) -> bool:
        """Verifica si una sala existe.

        Args:
            room_id: El identificador de la sala.

        Returns:
            True si existe, False en caso contrario.
        """
        return room_id in self._rooms

    def count(self) -> int:
        """Cuenta el número total de salas.

        Returns:
            Número de salas existentes.
        """
        return len(self._rooms)

    def clear(self) -> None:
        """Limpia todas las salas.

        Útil para testing.
        """
        self._rooms.clear()

    @classmethod
    def reset_instance(cls) -> None:
        """Resetea la instancia singleton (útil para tests)."""
        if cls._instance is not None:
            cls._instance._rooms.clear()


def get_room_repository() -> InMemoryRoomRepository:
    """Obtiene la instancia del repositorio de salas.

    Returns:
        La instancia singleton del repositorio.
    """
    return InMemoryRoomRepository()


def reset_room_repository() -> None:
    """Resetea el repositorio (útil para tests)."""
    InMemoryRoomRepository.reset_instance()
