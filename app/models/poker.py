"""Modelos de datos para la aplicación Scrum Poker."""

from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Escalas de votación predefinidas
SCALES = {
    "fibonacci": ["0", "1", "2", "3", "5", "8", "13", "21", "34", "55", "89", "?", "☕"],
    "modified_fibonacci": [
        "0",
        "0.5",
        "1",
        "2",
        "3",
        "5",
        "8",
        "13",
        "20",
        "40",
        "100",
        "?",
        "☕",
    ],
    "powers_of_2": ["0", "1", "2", "4", "8", "16", "32", "64", "?", "☕"],
    "t_shirt": ["XXS", "XS", "S", "M", "L", "XL", "XXL", "?", "☕"],
    "linear": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "?", "☕"],
}


class RoomStatus(str, Enum):
    """Estado de una sala de votación."""

    VOTING = "voting"
    REVEALED = "revealed"


class VotingMode(str, Enum):
    """Modo de votación de la sala."""

    ANONYMOUS = "anonymous"  # No se muestra quién votó qué
    PUBLIC = "public"  # Se muestra quién votó qué


@dataclass
class Player:
    """Representa un jugador en la sala."""

    id: str
    name: str
    is_observer: bool = False
    is_facilitator: bool = False  # Nuevo: rol de facilitador
    vote: str | None = None  # Voto como string para soportar escalas dinámicas
    connected: bool = True
    joined_at: datetime = field(default_factory=datetime.now)

    def reset_vote(self) -> None:
        """Resetea el voto del jugador."""
        self.vote = None

    def has_voted(self) -> bool:
        """Verifica si el jugador ha votado."""
        return self.vote is not None


@dataclass
class StoryHistory:
    """Representa una historia votada con su historial."""

    story_name: str
    votes: dict[str, str]  # player_name -> vote_value
    vote_summary: dict[str, int]  # vote_value -> count
    average: float | None
    rounded_average: str | None  # Promedio redondeado a la escala
    voted_at: datetime = field(default_factory=datetime.now)
    round_number: int = 1  # Número de ronda de votación
    is_superseded: bool = False  # True si fue reemplazada por una re-votación


@dataclass
class Room:
    """Representa una sala de Scrum Poker."""

    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    status: RoomStatus = RoomStatus.VOTING
    voting_mode: VotingMode = VotingMode.PUBLIC  # Nuevo: modo de votación
    players: dict[str, Player] = field(default_factory=dict)
    story_name: str = ""
    history: list[StoryHistory] = field(default_factory=list)  # Nuevo: historial
    voting_scale: str = "modified_fibonacci"  # Escala de votación
    custom_scale: list[str] = field(default_factory=list)  # Escala personalizada

    def add_player(self, player: Player) -> None:
        """Añade un jugador a la sala."""
        self.players[player.id] = player

    def remove_player(self, player_id: str) -> None:
        """Remueve un jugador de la sala."""
        self.players.pop(player_id, None)

    def get_player(self, player_id: str) -> Player | None:
        """Obtiene un jugador por su ID."""
        return self.players.get(player_id)

    def find_player_by_name(self, name: str) -> Player | None:
        """Busca un jugador por su nombre."""
        for player in self.players.values():
            if player.name.lower() == name.lower():
                return player
        return None

    def get_facilitator(self) -> Player | None:
        """Obtiene el facilitador de la sala."""
        for player in self.players.values():
            if player.is_facilitator:
                return player
        return None

    def get_current_scale(self) -> list[str]:
        """Obtiene la escala de votación actual."""
        if self.custom_scale:
            return self.custom_scale
        return SCALES.get(self.voting_scale, SCALES["modified_fibonacci"])

    def round_to_scale(self, value: float) -> str | None:
        """Redondea un valor al más cercano en la escala."""
        scale = self.get_current_scale()
        numeric_scale = []

        for item in scale:
            try:
                numeric_scale.append((float(item), item))
            except ValueError:
                continue  # Ignora valores no numéricos

        if not numeric_scale:
            return None

        # Encuentra el valor más cercano
        closest = min(numeric_scale, key=lambda x: abs(x[0] - value))
        return closest[1]

    def get_total_story_points(self) -> float:
        """Calcula el total de story points de todas las historias (solo las vigentes)."""
        total = 0.0

        # Solo sumar las historias que no han sido reemplazadas
        for story in self.history:
            is_superseded = getattr(story, "is_superseded", False)
            if not is_superseded and story.rounded_average:
                with suppress(ValueError):
                    # Si no es numérico, se ignora automáticamente
                    total += float(story.rounded_average)

        return total

    def update_or_add_history(
        self,
        story_name: str,
        votes: dict,
        vote_summary: dict,
        average: float | None,
        rounded_average: str | None,
    ) -> None:
        """
        Agrega una historia al historial.
        Si ya existe, marca las anteriores como superseded y solo deja la última vigente.
        """
        # Eliminar todas las entradas previas de la historia
        self.history = [h for h in self.history if h.story_name != story_name]
        story = StoryHistory(
            story_name=story_name,
            votes=votes.copy(),
            vote_summary=vote_summary.copy(),
            average=average,
            rounded_average=rounded_average,
            round_number=1,
            is_superseded=False,
        )
        self.history.append(story)

    def reset_votes(self) -> None:
        """Resetea todos los votos y vuelve al estado de votación."""
        # Guardar en historial si había una historia activa con votos
        if self.story_name:
            votes = {}
            vote_summary: dict[str, int] = {}
            numeric_votes = []

            # Calcular todos los valores antes de resetear
            for player in self.players.values():
                if not player.is_observer and player.vote:
                    votes[player.name] = player.vote
                    vote_summary[player.vote] = vote_summary.get(player.vote, 0) + 1

                    # Calcular promedio
                    try:
                        numeric_votes.append(float(player.vote))
                    except ValueError:
                        continue  # Ignora votos no numéricos como ? o ☕

            if votes:  # Solo guardar si hubo votos
                average = sum(numeric_votes) / len(numeric_votes) if numeric_votes else None
                rounded_average = self.round_to_scale(average) if average is not None else None
                self.update_or_add_history(
                    story_name=self.story_name,
                    votes=votes,
                    vote_summary=vote_summary,
                    average=average,
                    rounded_average=rounded_average,
                )
        # Resetear votos y limpiar nombre de historia
        for player in self.players.values():
            player.reset_vote()
        self.story_name = ""  # Limpiar el nombre de la historia para la nueva ronda
        self.status = RoomStatus.VOTING

    def reveal_votes(self) -> None:
        """Revela todos los votos."""
        self.status = RoomStatus.REVEALED

    def all_voted(self) -> bool:
        """Verifica si todos los jugadores activos y conectados han votado."""
        active_players = [p for p in self.players.values() if not p.is_observer and p.connected]
        if not active_players:
            return False
        return all(p.has_voted() for p in active_players)

    def get_vote_summary(self) -> dict[str, int]:
        """Obtiene un resumen de los votos."""
        if self.status != RoomStatus.REVEALED:
            return {}

        summary: dict[str, int] = {}
        for player in self.players.values():
            if not player.is_observer and player.vote:
                summary[player.vote] = summary.get(player.vote, 0) + 1

        return summary

    def get_average_vote(self) -> float | None:
        """Calcula el promedio de los votos numéricos."""
        if self.status != RoomStatus.REVEALED:
            return None

        numeric_votes = []
        for player in self.players.values():
            if not player.is_observer and player.vote:
                try:
                    numeric_votes.append(float(player.vote))
                except ValueError:
                    continue  # Ignora votos no numéricos como ? o ☕

        return sum(numeric_votes) / len(numeric_votes) if numeric_votes else None
