"""Enumeraciones del dominio."""

from enum import Enum


class RoomStatus(str, Enum):
    """Estado de una sala de votación."""

    VOTING = "voting"
    REVEALED = "revealed"


class VotingMode(str, Enum):
    """Modo de votación de la sala."""

    ANONYMOUS = "anonymous"  # No se muestra quién votó qué
    PUBLIC = "public"  # Se muestra quién votó qué
