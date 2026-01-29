"""Casos de uso para gestión de salas."""

from dataclasses import dataclass
from uuid import uuid4

from app.domain.aggregates import Room
from app.domain.entities import Player
from app.domain.repositories import RoomRepository


class RoomNotFoundError(Exception):
    """Error cuando no se encuentra una sala."""

    def __init__(self, room_id: str) -> None:
        self.room_id = room_id
        super().__init__(f"Sala no encontrada: {room_id}")


class RoomFullError(Exception):
    """Error cuando la sala está llena."""

    def __init__(self, room_id: str, max_players: int) -> None:
        self.room_id = room_id
        self.max_players = max_players
        super().__init__(f"La sala está llena (máximo {max_players} jugadores)")


class InvalidRoomNameError(Exception):
    """Error cuando el nombre de la sala es inválido."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidPlayerNameError(Exception):
    """Error cuando el nombre del jugador es inválido."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass
class CreateRoomResult:
    """Resultado de crear una sala."""

    room: Room


@dataclass
class JoinRoomResult:
    """Resultado de unirse a una sala."""

    room_id: str
    player_id: str
    player_name: str
    is_reconnect: bool = False


class CreateRoomUseCase:
    """Caso de uso para crear una sala."""

    MAX_NAME_LENGTH = 100

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(self, room_name: str) -> CreateRoomResult:
        """Crea una nueva sala de Scrum Poker.

        Args:
            room_name: Nombre de la sala.

        Returns:
            CreateRoomResult con la sala creada.

        Raises:
            InvalidRoomNameError: Si el nombre es inválido.
        """
        # Validar nombre
        name = room_name.strip()
        if not name:
            raise InvalidRoomNameError("El nombre de la sala no puede estar vacío")
        if len(name) > self.MAX_NAME_LENGTH:
            raise InvalidRoomNameError(
                f"Nombre de sala muy largo (máximo {self.MAX_NAME_LENGTH} caracteres)"
            )

        # Crear sala
        room_id = str(uuid4())[:8]
        room = Room.create(room_id=room_id, name=name)

        # Guardar
        self.room_repository.save(room)

        return CreateRoomResult(room=room)


class GetRoomUseCase:
    """Caso de uso para obtener una sala."""

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(self, room_id: str) -> Room:
        """Obtiene una sala por su ID.

        Args:
            room_id: ID de la sala.

        Returns:
            La sala encontrada.

        Raises:
            RoomNotFoundError: Si la sala no existe.
        """
        room = self.room_repository.get_by_id(room_id)
        if not room:
            raise RoomNotFoundError(room_id)
        return room


class ListRoomsUseCase:
    """Caso de uso para listar salas."""

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(self) -> list[Room]:
        """Lista todas las salas activas.

        Returns:
            Lista de salas.
        """
        return self.room_repository.list_all()


class DeleteRoomUseCase:
    """Caso de uso para eliminar una sala."""

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(self, room_id: str) -> None:
        """Elimina una sala.

        Args:
            room_id: ID de la sala a eliminar.

        Raises:
            RoomNotFoundError: Si la sala no existe.
        """
        if not self.room_repository.exists(room_id):
            raise RoomNotFoundError(room_id)
        self.room_repository.delete(room_id)


class JoinRoomUseCase:
    """Caso de uso para unirse a una sala."""

    MAX_PLAYER_NAME_LENGTH = 50
    MAX_PLAYERS_PER_ROOM = 20

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(
        self,
        room_id: str,
        player_name: str,
        is_observer: bool = False,
    ) -> JoinRoomResult:
        """Une un jugador a una sala.

        Soporta reconexión si el jugador ya existe por nombre.

        Args:
            room_id: ID de la sala.
            player_name: Nombre del jugador.
            is_observer: Si el jugador es observador.

        Returns:
            JoinRoomResult con los datos del jugador.

        Raises:
            RoomNotFoundError: Si la sala no existe.
            InvalidPlayerNameError: Si el nombre es inválido.
            RoomFullError: Si la sala está llena.
        """
        # Obtener sala
        room = self.room_repository.get_by_id(room_id)
        if not room:
            raise RoomNotFoundError(room_id)

        # Validar nombre
        name = player_name.strip()
        if not name:
            raise InvalidPlayerNameError("El nombre del jugador no puede estar vacío")
        if len(name) > self.MAX_PLAYER_NAME_LENGTH:
            raise InvalidPlayerNameError(
                f"Nombre muy largo (máximo {self.MAX_PLAYER_NAME_LENGTH} caracteres)"
            )

        # Verificar reconexión
        existing_player = room.find_player_by_name(name)
        if existing_player:
            existing_player.reconnect()
            existing_player.is_observer = is_observer
            self.room_repository.save(room)
            return JoinRoomResult(
                room_id=room_id,
                player_id=existing_player.id,
                player_name=existing_player.name,
                is_reconnect=True,
            )

        # Verificar límite de jugadores
        if room.player_count() >= self.MAX_PLAYERS_PER_ROOM:
            raise RoomFullError(room_id, self.MAX_PLAYERS_PER_ROOM)

        # Crear nuevo jugador
        player_id = str(uuid4())[:8]
        is_facilitator = room.player_count() == 0  # Primer jugador es facilitador

        player = Player.create(
            player_id=player_id,
            name=name,
            is_observer=is_observer,
            is_facilitator=is_facilitator,
        )
        room.add_player(player)

        # Guardar
        self.room_repository.save(room)

        return JoinRoomResult(
            room_id=room_id,
            player_id=player_id,
            player_name=name,
            is_reconnect=False,
        )
