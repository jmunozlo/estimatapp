"""Gestor de salas de Scrum Poker.

Este módulo proporciona compatibilidad con el código existente
delegando al repositorio de infraestructura.
"""

from uuid import uuid4

from app.domain import Room
from app.infrastructure import get_room_repository


class RoomManager:
    """Gestiona las salas de Scrum Poker.

    Esta clase actúa como adaptador entre el código existente
    y el nuevo repositorio de infraestructura.
    """

    def __init__(self) -> None:
        """Inicializa el gestor de salas."""
        self._repository = get_room_repository()

    @property
    def rooms(self) -> dict[str, Room]:
        """Propiedad para acceso directo a las salas (compatibilidad)."""
        return {room.id: room for room in self._repository.list_all()}

    def create_room(self, name: str) -> Room:
        """Crea una nueva sala."""
        room_id = str(uuid4())[:8]
        room = Room.create(room_id=room_id, name=name)
        self._repository.save(room)
        return room

    def get_room(self, room_id: str) -> Room | None:
        """Obtiene una sala por su ID."""
        return self._repository.get_by_id(room_id)

    def delete_room(self, room_id: str) -> None:
        """Elimina una sala."""
        self._repository.delete(room_id)

    def list_rooms(self) -> list[Room]:
        """Lista todas las salas activas."""
        return self._repository.list_all()


# Instancia global del gestor de salas
room_manager = RoomManager()
