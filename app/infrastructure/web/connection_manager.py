"""Gestor de conexiones WebSocket."""

from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Gestiona las conexiones WebSocket de los jugadores.

    Esta clase es parte de la capa de infraestructura y maneja
    la comunicación en tiempo real con los clientes.
    Implementa el patrón Singleton.
    """

    _instance: "ConnectionManager | None" = None

    def __new__(cls) -> "ConnectionManager":
        """Implementa el patrón Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.active_connections = {}
        return cls._instance

    def __init__(self) -> None:
        """Inicializa el gestor de conexiones (solo la primera vez)."""
        # active_connections se inicializa en __new__

    async def connect(self, websocket: WebSocket, room_id: str, player_id: str) -> None:
        """Conecta un jugador a una sala.

        Args:
            websocket: La conexión WebSocket.
            room_id: ID de la sala.
            player_id: ID del jugador.
        """
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][player_id] = websocket

    def disconnect(self, room_id: str, player_id: str) -> None:
        """Desconecta un jugador de una sala.

        Args:
            room_id: ID de la sala.
            player_id: ID del jugador.
        """
        if room_id in self.active_connections:
            self.active_connections[room_id].pop(player_id, None)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def send_to_player(self, room_id: str, player_id: str, message: dict[str, Any]) -> bool:
        """Envía un mensaje a un jugador específico.

        Args:
            room_id: ID de la sala.
            player_id: ID del jugador.
            message: Mensaje a enviar.

        Returns:
            True si se envió correctamente, False si falló.
        """
        if room_id not in self.active_connections:
            return False

        connection = self.active_connections[room_id].get(player_id)
        if not connection:
            return False

        try:
            await connection.send_json(message)
            return True
        except Exception:
            self.disconnect(room_id, player_id)
            return False

    async def broadcast(self, room_id: str, message: dict[str, Any]) -> None:
        """Envía un mensaje a todos los jugadores de una sala.

        Args:
            room_id: ID de la sala.
            message: Mensaje a enviar.
        """
        if room_id not in self.active_connections:
            return

        disconnected = []
        for player_id, connection in self.active_connections[room_id].items():
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(player_id)

        # Limpia conexiones desconectadas
        for player_id in disconnected:
            self.disconnect(room_id, player_id)

    def get_connection_count(self, room_id: str) -> int:
        """Obtiene el número de conexiones en una sala.

        Args:
            room_id: ID de la sala.

        Returns:
            Número de conexiones activas.
        """
        if room_id not in self.active_connections:
            return 0
        return len(self.active_connections[room_id])

    def is_connected(self, room_id: str, player_id: str) -> bool:
        """Verifica si un jugador está conectado.

        Args:
            room_id: ID de la sala.
            player_id: ID del jugador.

        Returns:
            True si está conectado.
        """
        if room_id not in self.active_connections:
            return False
        return player_id in self.active_connections[room_id]


def get_connection_manager() -> ConnectionManager:
    """Obtiene la instancia del gestor de conexiones.

    Returns:
        La instancia singleton del gestor.
    """
    return ConnectionManager()
