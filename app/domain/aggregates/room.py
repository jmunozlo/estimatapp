"""Aggregate Root Room del dominio.

Room es el aggregate root principal que encapsula toda la lógica
de negocio relacionada con las sesiones de estimación.
"""

from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.entities.enums import RoomStatus, VotingMode
from app.domain.entities.player import Player
from app.domain.entities.story import StoryHistory
from app.domain.value_objects.voting import PREDEFINED_SCALES, VotingScale


@dataclass
class Room:
    """Aggregate Root para una sala de Scrum Poker.

    Esta es la entidad principal que gestiona todo el flujo de estimación,
    incluyendo jugadores, votos, escalas y el historial de historias.
    """

    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    status: RoomStatus = RoomStatus.VOTING
    voting_mode: VotingMode = VotingMode.PUBLIC
    players: dict[str, Player] = field(default_factory=dict)
    story_name: str = ""
    history: list[StoryHistory] = field(default_factory=list)
    voting_scale: str = "modified_fibonacci"
    custom_scale: list[str] = field(default_factory=list)

    # --- Gestión de Jugadores ---

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
        """Busca un jugador por su nombre (case-insensitive)."""
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

    def get_active_voters(self) -> list[Player]:
        """Obtiene los jugadores activos que pueden votar."""
        return [p for p in self.players.values() if not p.is_observer and p.connected]

    def get_connected_players(self) -> list[Player]:
        """Obtiene los jugadores conectados."""
        return [p for p in self.players.values() if p.connected]

    def player_count(self) -> int:
        """Retorna el número de jugadores en la sala."""
        return len(self.players)

    # --- Gestión de Escalas ---

    def get_current_scale(self) -> list[str]:
        """Obtiene la escala de votación actual."""
        if self.custom_scale:
            return self.custom_scale
        return PREDEFINED_SCALES.get(self.voting_scale, PREDEFINED_SCALES["modified_fibonacci"])

    def get_voting_scale(self) -> VotingScale:
        """Obtiene la escala de votación como Value Object."""
        if self.custom_scale:
            return VotingScale.custom(self.custom_scale)
        return VotingScale.from_predefined(self.voting_scale)

    def set_scale(self, scale_name: str) -> None:
        """Establece una escala predefinida."""
        self.voting_scale = scale_name
        self.custom_scale = []

    def set_custom_scale(self, values: list[str]) -> None:
        """Establece una escala personalizada."""
        clean_values = [v.strip() for v in values if v and str(v).strip()]
        self.custom_scale = clean_values
        self.voting_scale = "custom"

    def round_to_scale(self, value: float) -> str | None:
        """Redondea un valor al más cercano en la escala."""
        return self.get_voting_scale().round_to_scale(value)

    def is_valid_vote(self, vote_value: str) -> bool:
        """Verifica si un voto es válido según la escala actual."""
        return vote_value in self.get_current_scale()

    # --- Flujo de Votación ---

    def reveal_votes(self) -> None:
        """Revela todos los votos."""
        self.status = RoomStatus.REVEALED

    def is_revealed(self) -> bool:
        """Verifica si los votos están revelados."""
        return self.status == RoomStatus.REVEALED

    def is_voting(self) -> bool:
        """Verifica si la sala está en modo votación."""
        return self.status == RoomStatus.VOTING

    def all_voted(self) -> bool:
        """Verifica si todos los jugadores activos y conectados han votado."""
        active_players = self.get_active_voters()
        if not active_players:
            return False
        return all(p.has_voted() for p in active_players)

    def get_vote_summary(self) -> dict[str, int]:
        """Obtiene un resumen de los votos (solo si revelados)."""
        if self.status != RoomStatus.REVEALED:
            return {}

        summary: dict[str, int] = {}
        for player in self.players.values():
            if not player.is_observer and player.vote:
                summary[player.vote] = summary.get(player.vote, 0) + 1

        return summary

    def get_average_vote(self) -> float | None:
        """Calcula el promedio de los votos numéricos (solo si revelados)."""
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

    # --- Gestión de Historias ---

    def set_story_name(self, name: str) -> None:
        """Establece el nombre de la historia actual."""
        self.story_name = name

    def update_or_add_history(
        self,
        story_name: str,
        votes: dict[str, str],
        vote_summary: dict[str, int],
        average: float | None,
        rounded_average: str | None,
    ) -> None:
        """Agrega una historia al historial. Si ya existe, marca las anteriores como superseded."""
        # Contar cuántas rondas previas hay para esta historia y marcarlas como superseded
        round_number = 1
        for story in self.history:
            if story.story_name == story_name:
                story.is_superseded = True  # Marcar la anterior como reemplazada
                round_number = max(round_number, story.round_number + 1)

        # Agregar nueva entrada (nunca reemplazar)
        story = StoryHistory.create(
            story_name=story_name,
            votes=votes,
            vote_summary=vote_summary,
            average=average,
            rounded_average=rounded_average,
            round_number=round_number,
            is_superseded=False,
        )
        self.history.append(story)

    def reset_votes(self) -> None:
        """Resetea todos los votos y vuelve al estado de votación.

        Si había una historia activa con votos, guarda en el historial.
        """
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
                        continue  # Ignora votos no numéricos

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
        self.story_name = ""
        self.status = RoomStatus.VOTING

    def get_total_story_points(self) -> float:
        """Calcula el total de story points de todas las historias vigentes.

        Solo suma las historias que no han sido reemplazadas (is_superseded=False).
        """
        total = 0.0

        for story in self.history:
            # Solo sumar las historias que no han sido reemplazadas
            if not story.is_superseded and story.rounded_average:
                with suppress(ValueError):
                    total += float(story.rounded_average)

        return total

    # --- Modo de Votación ---

    def toggle_voting_mode(self) -> VotingMode:
        """Alterna entre modo público y anónimo."""
        if self.voting_mode == VotingMode.PUBLIC:
            self.voting_mode = VotingMode.ANONYMOUS
        else:
            self.voting_mode = VotingMode.PUBLIC
        return self.voting_mode

    def is_anonymous(self) -> bool:
        """Verifica si el modo de votación es anónimo."""
        return self.voting_mode == VotingMode.ANONYMOUS

    # --- Factory Methods ---

    @classmethod
    def create(cls, room_id: str, name: str) -> "Room":
        """Factory method para crear una nueva sala."""
        return cls(id=room_id, name=name)

    # --- Serialización ---

    def to_dict(self) -> dict:
        """Convierte la sala a un diccionario para respuestas API."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "player_count": len(self.players),
        }
