"""Infrastructure Web (FastAPI)."""

from app.infrastructure.web.connection_manager import (
    ConnectionManager,
    get_connection_manager,
)

__all__ = [
    "ConnectionManager",
    "get_connection_manager",
]
