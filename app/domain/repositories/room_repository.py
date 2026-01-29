"""Interfaz del repositorio de salas.

Define el contrato que deben implementar los repositorios de Room.
"""

from abc import ABC, abstractmethod

from app.domain.aggregates.room import Room


class RoomRepository(ABC):
    """Interfaz abstracta para el repositorio de salas.

    Define las operaciones que cualquier implementación de repositorio
    de salas debe proporcionar.
    """

    @abstractmethod
    def save(self, room: Room) -> None:
        """Guarda una sala (crear o actualizar).

        Args:
            room: La sala a guardar.
        """

    @abstractmethod
    def get_by_id(self, room_id: str) -> Room | None:
        """Obtiene una sala por su ID.

        Args:
            room_id: El identificador de la sala.

        Returns:
            La sala si existe, None en caso contrario.
        """

    @abstractmethod
    def delete(self, room_id: str) -> bool:
        """Elimina una sala.

        Args:
            room_id: El identificador de la sala a eliminar.

        Returns:
            True si se eliminó, False si no existía.
        """

    @abstractmethod
    def list_all(self) -> list[Room]:
        """Lista todas las salas.

        Returns:
            Lista de todas las salas existentes.
        """

    @abstractmethod
    def exists(self, room_id: str) -> bool:
        """Verifica si una sala existe.

        Args:
            room_id: El identificador de la sala.

        Returns:
            True si existe, False en caso contrario.
        """

    @abstractmethod
    def count(self) -> int:
        """Cuenta el número total de salas.

        Returns:
            Número de salas existentes.
        """
