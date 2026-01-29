"""Rutas de la aplicación."""

from app.routes.rooms import router as rooms_router
from app.routes.websocket import router as websocket_router

__all__ = ["rooms_router", "websocket_router"]
