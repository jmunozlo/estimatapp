"""Infrastructure Layer - Implementaciones concretas.

Este módulo contiene las implementaciones de infraestructura:
- Repositorios en memoria y PostgreSQL
- Gestión de conexiones WebSocket
- Validación JWT y middleware de autenticación
- Adaptadores HTTP/FastAPI
"""

from app.infrastructure.repositories import (
    InMemoryRoomRepository,
    PostgresRoomRepository,
    get_room_repository,
    reset_room_repository,
)
from app.infrastructure.web import (
    ConnectionManager,
    get_connection_manager,
)

__all__ = [
    # Web
    "ConnectionManager",
    # Repositories
    "InMemoryRoomRepository",
    "PostgresRoomRepository",
    "get_connection_manager",
    "get_room_repository",
    "reset_room_repository",
]
