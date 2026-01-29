"""Gestor de conexiones WebSocket.

Este módulo proporciona compatibilidad con el código existente
re-exportando el gestor de conexiones de infraestructura.
"""

from app.infrastructure.web import ConnectionManager, get_connection_manager

# Instancia global del gestor de conexiones para compatibilidad
ws_manager = get_connection_manager()

__all__ = ["ConnectionManager", "ws_manager"]
