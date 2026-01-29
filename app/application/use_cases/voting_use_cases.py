"""Casos de uso para la votación."""

from dataclasses import dataclass

from app.domain.aggregates import Room
from app.domain.entities import Player
from app.domain.repositories import RoomRepository


class RoomNotFoundError(Exception):
    """Error cuando no se encuentra una sala."""

    def __init__(self, room_id: str) -> None:
        self.room_id = room_id
        super().__init__(f"Sala no encontrada: {room_id}")


class PlayerNotFoundError(Exception):
    """Error cuando no se encuentra un jugador."""

    def __init__(self, player_id: str) -> None:
        self.player_id = player_id
        super().__init__(f"Jugador no encontrado: {player_id}")


class UnauthorizedError(Exception):
    """Error cuando el jugador no tiene permisos."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidVoteError(Exception):
    """Error cuando el voto es inválido."""

    def __init__(self, vote_value: str) -> None:
        self.vote_value = vote_value
        super().__init__(f"Voto inválido: {vote_value} no está en la escala actual")


class InvalidScaleError(Exception):
    """Error cuando la escala es inválida."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidStoryNameError(Exception):
    """Error cuando el nombre de la historia es inválido."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass
class VoteResult:
    """Resultado de votar."""

    success: bool
    vote_value: str | None


class VoteUseCase:
    """Caso de uso para votar."""

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(
        self,
        room_id: str,
        player_id: str,
        vote_value: str | None,
    ) -> VoteResult:
        """Registra un voto de un jugador.

        Args:
            room_id: ID de la sala.
            player_id: ID del jugador.
            vote_value: Valor del voto (None para quitar voto).

        Returns:
            VoteResult con el resultado.

        Raises:
            RoomNotFoundError: Si la sala no existe.
            PlayerNotFoundError: Si el jugador no existe.
            InvalidVoteError: Si el voto no está en la escala.
        """
        room = self._get_room(room_id)
        player = self._get_player(room, player_id)

        # Si es None, quitar voto
        if vote_value is None:
            player.set_vote(None)
            self.room_repository.save(room)
            return VoteResult(success=True, vote_value=None)

        # Validar voto
        if not room.is_valid_vote(vote_value):
            raise InvalidVoteError(vote_value)

        player.set_vote(vote_value)
        self.room_repository.save(room)

        return VoteResult(success=True, vote_value=vote_value)

    def _get_room(self, room_id: str) -> Room:
        room = self.room_repository.get_by_id(room_id)
        if not room:
            raise RoomNotFoundError(room_id)
        return room

    def _get_player(self, room: Room, player_id: str) -> Player:
        player = room.get_player(player_id)
        if not player:
            raise PlayerNotFoundError(player_id)
        return player


class RevealVotesUseCase:
    """Caso de uso para revelar votos."""

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(self, room_id: str, player_id: str) -> None:
        """Revela los votos (solo facilitador).

        Args:
            room_id: ID de la sala.
            player_id: ID del jugador que intenta revelar.

        Raises:
            RoomNotFoundError: Si la sala no existe.
            PlayerNotFoundError: Si el jugador no existe.
            UnauthorizedError: Si no es el facilitador.
        """
        room = self._get_room(room_id)
        player = self._get_player(room, player_id)

        if not player.is_facilitator:
            raise UnauthorizedError("Solo el facilitador puede revelar los votos")

        room.reveal_votes()
        self.room_repository.save(room)

    def _get_room(self, room_id: str) -> Room:
        room = self.room_repository.get_by_id(room_id)
        if not room:
            raise RoomNotFoundError(room_id)
        return room

    def _get_player(self, room: Room, player_id: str) -> Player:
        player = room.get_player(player_id)
        if not player:
            raise PlayerNotFoundError(player_id)
        return player


class ResetVotesUseCase:
    """Caso de uso para resetear votos."""

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(self, room_id: str, player_id: str) -> None:
        """Resetea los votos (solo facilitador).

        Args:
            room_id: ID de la sala.
            player_id: ID del jugador que intenta resetear.

        Raises:
            RoomNotFoundError: Si la sala no existe.
            PlayerNotFoundError: Si el jugador no existe.
            UnauthorizedError: Si no es el facilitador.
        """
        room = self._get_room(room_id)
        player = self._get_player(room, player_id)

        if not player.is_facilitator:
            raise UnauthorizedError("Solo el facilitador puede iniciar una nueva ronda")

        room.reset_votes()
        self.room_repository.save(room)

    def _get_room(self, room_id: str) -> Room:
        room = self.room_repository.get_by_id(room_id)
        if not room:
            raise RoomNotFoundError(room_id)
        return room

    def _get_player(self, room: Room, player_id: str) -> Player:
        player = room.get_player(player_id)
        if not player:
            raise PlayerNotFoundError(player_id)
        return player


class SetStoryNameUseCase:
    """Caso de uso para establecer el nombre de la historia."""

    MAX_STORY_NAME_LENGTH = 200

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(self, room_id: str, story_name: str) -> None:
        """Establece el nombre de la historia actual.

        Args:
            room_id: ID de la sala.
            story_name: Nombre de la historia.

        Raises:
            RoomNotFoundError: Si la sala no existe.
            InvalidStoryNameError: Si el nombre es muy largo.
        """
        room = self.room_repository.get_by_id(room_id)
        if not room:
            raise RoomNotFoundError(room_id)

        name = story_name.strip()
        if len(name) > self.MAX_STORY_NAME_LENGTH:
            raise InvalidStoryNameError(
                f"Historia muy larga (máximo {self.MAX_STORY_NAME_LENGTH} caracteres)"
            )

        room.set_story_name(name)
        self.room_repository.save(room)


class ToggleVotingModeUseCase:
    """Caso de uso para cambiar el modo de votación."""

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(self, room_id: str, player_id: str) -> str:
        """Alterna el modo de votación (solo facilitador).

        Args:
            room_id: ID de la sala.
            player_id: ID del jugador que intenta cambiar.

        Returns:
            El nuevo modo de votación.

        Raises:
            RoomNotFoundError: Si la sala no existe.
            PlayerNotFoundError: Si el jugador no existe.
            UnauthorizedError: Si no es el facilitador.
        """
        room = self.room_repository.get_by_id(room_id)
        if not room:
            raise RoomNotFoundError(room_id)

        player = room.get_player(player_id)
        if not player:
            raise PlayerNotFoundError(player_id)

        if not player.is_facilitator:
            raise UnauthorizedError("Solo el facilitador puede cambiar el modo de votación")

        new_mode = room.toggle_voting_mode()
        self.room_repository.save(room)

        return new_mode.value


class ChangeScaleUseCase:
    """Caso de uso para cambiar la escala de votación."""

    MIN_SCALE_VALUES = 2

    def __init__(self, room_repository: RoomRepository) -> None:
        self.room_repository = room_repository

    def execute(self, room_id: str, player_id: str, scale_name: str) -> None:
        """Cambia la escala de votación predefinida (solo facilitador).

        Args:
            room_id: ID de la sala.
            player_id: ID del jugador que intenta cambiar.
            scale_name: Nombre de la escala predefinida.

        Raises:
            RoomNotFoundError: Si la sala no existe.
            PlayerNotFoundError: Si el jugador no existe.
            UnauthorizedError: Si no es el facilitador.
        """
        room = self.room_repository.get_by_id(room_id)
        if not room:
            raise RoomNotFoundError(room_id)

        player = room.get_player(player_id)
        if not player:
            raise PlayerNotFoundError(player_id)

        if not player.is_facilitator:
            raise UnauthorizedError("Solo el facilitador puede cambiar la escala de votación")

        room.set_scale(scale_name)
        self.room_repository.save(room)

    def execute_custom(self, room_id: str, player_id: str, values: list[str]) -> None:
        """Establece una escala personalizada (solo facilitador).

        Args:
            room_id: ID de la sala.
            player_id: ID del jugador que intenta cambiar.
            values: Lista de valores de la escala.

        Raises:
            RoomNotFoundError: Si la sala no existe.
            PlayerNotFoundError: Si el jugador no existe.
            UnauthorizedError: Si no es el facilitador.
            InvalidScaleError: Si la escala es inválida.
        """
        room = self.room_repository.get_by_id(room_id)
        if not room:
            raise RoomNotFoundError(room_id)

        player = room.get_player(player_id)
        if not player:
            raise PlayerNotFoundError(player_id)

        if not player.is_facilitator:
            raise UnauthorizedError("Solo el facilitador puede establecer una escala personalizada")

        if not values or not isinstance(values, list):
            raise InvalidScaleError("La escala personalizada no puede estar vacía")

        clean_values = [v.strip() for v in values if v and str(v).strip()]
        if len(clean_values) < self.MIN_SCALE_VALUES:
            raise InvalidScaleError(
                f"La escala debe tener al menos {self.MIN_SCALE_VALUES} valores"
            )

        room.set_custom_scale(clean_values)
        self.room_repository.save(room)
