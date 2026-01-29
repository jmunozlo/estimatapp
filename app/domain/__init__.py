"""Domain Layer - Núcleo de la lógica de negocio.

Este módulo contiene las entidades, value objects, agregados y repositorios
que representan el dominio de la aplicación Scrum Poker.
"""

from app.domain.aggregates import Room
from app.domain.entities import Player, PlayerRole, RoomStatus, StoryHistory, VotingMode
from app.domain.repositories import RoomRepository
from app.domain.value_objects import (
    PREDEFINED_SCALES,
    PlayerId,
    PlayerName,
    RoomId,
    RoomName,
    StoryName,
    Vote,
    VoteSummary,
    VotingScale,
)

__all__ = [
    "PREDEFINED_SCALES",
    # Entities
    "Player",
    # Value Objects
    "PlayerId",
    "PlayerName",
    "PlayerRole",
    # Aggregates
    "Room",
    "RoomId",
    "RoomName",
    # Repositories
    "RoomRepository",
    "RoomStatus",
    "StoryHistory",
    "StoryName",
    "Vote",
    "VoteSummary",
    "VotingMode",
    "VotingScale",
]
