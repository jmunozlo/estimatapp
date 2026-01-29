"""Infrastructure Layer - Implementaciones concretas.

Este módulo contiene las implementaciones de infraestructura:
- Repositorios en memoria
- Gestión de conexiones WebSocket
- Adaptadores HTTP/FastAPI
"""

from app.infrastructure.repositories import (
    InMemoryRoomRepository,
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
    "get_connection_manager",
    "get_room_repository",
    "reset_room_repository",
]
