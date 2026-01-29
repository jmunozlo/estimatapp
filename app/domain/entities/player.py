"""Entidad Player del dominio."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PlayerRole(str, Enum):
    """Roles que puede tener un jugador."""

    VOTER = "voter"
    OBSERVER = "observer"
    FACILITATOR = "facilitator"


@dataclass
class Player:
    """Representa un jugador en la sala de estimación.

    Esta es una entidad del dominio que tiene identidad y estado mutable.
    """

    id: str
    name: str
    is_observer: bool = False
    is_facilitator: bool = False
    vote: str | None = None
    connected: bool = True
    joined_at: datetime = field(default_factory=datetime.now)

    def reset_vote(self) -> None:
        """Resetea el voto del jugador."""
        self.vote = None

    def has_voted(self) -> bool:
        """Verifica si el jugador ha votado."""
        return self.vote is not None

    def set_vote(self, vote_value: str | None) -> None:
        """Establece el voto del jugador."""
        self.vote = vote_value

    def can_vote(self) -> bool:
        """Verifica si el jugador puede votar."""
        return not self.is_observer and self.connected

    def disconnect(self) -> None:
        """Marca al jugador como desconectado."""
        self.connected = False

    def reconnect(self) -> None:
        """Marca al jugador como conectado."""
        self.connected = True

    def get_role(self) -> PlayerRole:
        """Obtiene el rol principal del jugador."""
        if self.is_facilitator:
            return PlayerRole.FACILITATOR
        if self.is_observer:
            return PlayerRole.OBSERVER
        return PlayerRole.VOTER

    def to_dict(self, include_vote: bool = False) -> dict:
        """Convierte el jugador a un diccionario."""
        data = {
            "id": self.id,
            "name": self.name,
            "is_observer": self.is_observer,
            "is_facilitator": self.is_facilitator,
            "connected": self.connected,
            "has_voted": self.has_voted(),
        }
        if include_vote and self.vote:
            data["vote"] = self.vote
        return data

    @classmethod
    def create(
        cls,
        player_id: str,
        name: str,
        is_observer: bool = False,
        is_facilitator: bool = False,
    ) -> "Player":
        """Factory method para crear un nuevo jugador."""
        return cls(
            id=player_id,
            name=name,
            is_observer=is_observer,
            is_facilitator=is_facilitator,
        )
