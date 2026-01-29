"""Modelos de datos para la aplicación.

Este módulo re-exporta las clases del dominio para mantener
compatibilidad con el código existente durante la migración a DDD.
"""

from app.domain import (
    PREDEFINED_SCALES,
    Player,
    Room,
    RoomStatus,
    StoryHistory,
    VotingMode,
)

# Alias para compatibilidad
SCALES = PREDEFINED_SCALES

__all__ = ["SCALES", "Player", "Room", "RoomStatus", "StoryHistory", "VotingMode"]
