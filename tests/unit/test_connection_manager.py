"""Tests para el ConnectionManager."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.web.connection_manager import ConnectionManager, get_connection_manager


class TestConnectionManager:
    """Tests para ConnectionManager."""

    @pytest.fixture
    def connection_manager(self):
        """Crea un ConnectionManager limpio para cada test."""
        manager = ConnectionManager()
        manager.active_connections = {}  # Reset para tests
        return manager

    @pytest.fixture
    def mock_websocket(self):
        """Crea un mock de WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_new_room(self, connection_manager, mock_websocket):
        """Verifica conexión a una sala nueva."""
        await connection_manager.connect(mock_websocket, "room1", "player1")

        mock_websocket.accept.assert_called_once()
        assert "room1" in connection_manager.active_connections
        assert "player1" in connection_manager.active_connections["room1"]

    @pytest.mark.asyncio
    async def test_connect_existing_room(self, connection_manager, mock_websocket):
        """Verifica conexión a una sala existente."""
        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()

        await connection_manager.connect(mock_websocket, "room1", "player1")
        await connection_manager.connect(mock_ws2, "room1", "player2")

        assert len(connection_manager.active_connections["room1"]) == 2

    def test_disconnect_player(self, connection_manager, mock_websocket):
        """Verifica desconexión de un jugador."""
        connection_manager.active_connections = {
            "room1": {"player1": mock_websocket, "player2": MagicMock()}
        }

        connection_manager.disconnect("room1", "player1")

        assert "player1" not in connection_manager.active_connections["room1"]
        assert "player2" in connection_manager.active_connections["room1"]

    def test_disconnect_last_player_removes_room(self, connection_manager, mock_websocket):
        """Verifica que desconectar el último jugador elimina la sala."""
        connection_manager.active_connections = {"room1": {"player1": mock_websocket}}

        connection_manager.disconnect("room1", "player1")

        assert "room1" not in connection_manager.active_connections

    def test_disconnect_nonexistent_room(self, connection_manager):
        """Verifica que desconectar de sala inexistente no falla."""
        connection_manager.disconnect("nonexistent", "player1")
        # No debe lanzar excepción

    def test_disconnect_nonexistent_player(self, connection_manager, mock_websocket):
        """Verifica que desconectar jugador inexistente no falla."""
        connection_manager.active_connections = {"room1": {"player1": mock_websocket}}

        connection_manager.disconnect("room1", "nonexistent")

        assert "player1" in connection_manager.active_connections["room1"]

    @pytest.mark.asyncio
    async def test_send_to_player_success(self, connection_manager, mock_websocket):
        """Verifica envío de mensaje a un jugador."""
        connection_manager.active_connections = {"room1": {"player1": mock_websocket}}

        result = await connection_manager.send_to_player("room1", "player1", {"type": "test"})

        assert result is True
        mock_websocket.send_json.assert_called_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_to_player_room_not_found(self, connection_manager):
        """Verifica que enviar a sala inexistente retorna False."""
        result = await connection_manager.send_to_player("nonexistent", "player1", {"type": "test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_player_player_not_found(self, connection_manager, mock_websocket):
        """Verifica que enviar a jugador inexistente retorna False."""
        connection_manager.active_connections = {"room1": {"player1": mock_websocket}}

        result = await connection_manager.send_to_player("room1", "nonexistent", {"type": "test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_player_handles_exception(self, connection_manager):
        """Verifica que errores al enviar desconectan al jugador."""
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock(side_effect=Exception("Connection error"))
        connection_manager.active_connections = {"room1": {"player1": mock_ws}}

        result = await connection_manager.send_to_player("room1", "player1", {"type": "test"})

        assert result is False
        assert "player1" not in connection_manager.active_connections.get("room1", {})

    @pytest.mark.asyncio
    async def test_broadcast_to_all_players(self, connection_manager):
        """Verifica broadcast a todos los jugadores."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        connection_manager.active_connections = {
            "room1": {"player1": mock_ws1, "player2": mock_ws2}
        }

        await connection_manager.broadcast("room1", {"type": "update"})

        mock_ws1.send_json.assert_called_once_with({"type": "update"})
        mock_ws2.send_json.assert_called_once_with({"type": "update"})

    @pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_room(self, connection_manager):
        """Verifica que broadcast a sala inexistente no falla."""
        await connection_manager.broadcast("nonexistent", {"type": "update"})
        # No debe lanzar excepción

    @pytest.mark.asyncio
    async def test_broadcast_disconnects_failed_connections(self, connection_manager):
        """Verifica que broadcast desconecta conexiones fallidas."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send_json = AsyncMock(side_effect=Exception("Connection error"))
        connection_manager.active_connections = {
            "room1": {"player1": mock_ws1, "player2": mock_ws2}
        }

        await connection_manager.broadcast("room1", {"type": "update"})

        assert "player1" in connection_manager.active_connections["room1"]
        assert "player2" not in connection_manager.active_connections["room1"]

    def test_get_connection_count(self, connection_manager, mock_websocket):
        """Verifica conteo de conexiones."""
        connection_manager.active_connections = {
            "room1": {"player1": mock_websocket, "player2": MagicMock()}
        }

        assert connection_manager.get_connection_count("room1") == 2

    def test_get_connection_count_nonexistent_room(self, connection_manager):
        """Verifica conteo de conexiones en sala inexistente."""
        assert connection_manager.get_connection_count("nonexistent") == 0

    def test_is_connected_true(self, connection_manager, mock_websocket):
        """Verifica que is_connected retorna True para jugador conectado."""
        connection_manager.active_connections = {"room1": {"player1": mock_websocket}}

        assert connection_manager.is_connected("room1", "player1") is True

    def test_is_connected_false_room_not_found(self, connection_manager):
        """Verifica que is_connected retorna False para sala inexistente."""
        assert connection_manager.is_connected("nonexistent", "player1") is False

    def test_is_connected_false_player_not_found(self, connection_manager, mock_websocket):
        """Verifica que is_connected retorna False para jugador no conectado."""
        connection_manager.active_connections = {"room1": {"player1": mock_websocket}}

        assert connection_manager.is_connected("room1", "nonexistent") is False


class TestGetConnectionManager:
    """Tests para la función get_connection_manager."""

    def test_get_connection_manager_returns_singleton(self):
        """Verifica que get_connection_manager retorna singleton."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2
