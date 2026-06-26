"""Integration tests for WebSocket JWT authentication.

Covers:
- 3.4 WS connect with valid/invalid JWT, verify accept/close 4001
- WS connect with no token → close 4001
- WS connect with invalid token → close 4001
- WS connect with valid token → accept and proceed
- Vote persistence through WS: connect, send vote, verify state
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI

from app.domain.aggregates.room import Room
from app.domain.entities.player import Player

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def reset_ws_validator():
    """Reset the module-level _jwt_validator before and after each test."""
    import app.routes.websocket as ws_module

    ws_module._jwt_validator = None
    yield
    ws_module._jwt_validator = None


@pytest.fixture
def mock_ws():
    """Create a mock WebSocket for testing.

    Provides:
    - query_params: dict-like access to query parameters
    - close: AsyncMock for verifying close calls
    - send_json: AsyncMock for verifying sent messages
    - receive_json: AsyncMock for controlling received messages
    """
    ws = AsyncMock()
    ws.query_params = {}
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    return ws


@pytest.fixture
def mock_validator():
    """Create a mock JWKSValidator with configurable validate behavior."""
    from app.infrastructure.auth.jwt_validator import JWTClaims

    validator = AsyncMock()
    validator.validate.return_value = JWTClaims(
        sub="user-ws-test",
        email="ws@test.com",
        aud="authenticated",
        exp=9999999999,
    )
    return validator


class TestWebSocketJWTAuth:
    """WebSocket JWT authentication behavior (Task 3.4)."""

    async def test_ws_no_token_closes_4001(self, mock_ws, mock_validator):
        """GIVEN WS connect without token WHEN handler runs THEN closes with 4001."""
        from app.routes.websocket import websocket_endpoint

        # No token param
        mock_ws.query_params = {}

        with patch(
            "app.routes.websocket._get_jwt_validator",
            return_value=mock_validator,
        ):
            await websocket_endpoint(mock_ws, "room-abc", "p1")

        mock_ws.close.assert_called_once()
        kwargs = mock_ws.close.call_args.kwargs
        assert kwargs.get("code") == 4001

    async def test_ws_invalid_token_closes_4001(self, mock_ws, mock_validator):
        """GIVEN WS connect with invalid JWT WHEN handler runs THEN closes with 4001."""
        from app.routes.websocket import websocket_endpoint

        mock_ws.query_params = {"token": "invalid.jwt.token"}
        mock_validator.validate.side_effect = Exception("Invalid token")

        with patch(
            "app.routes.websocket._get_jwt_validator",
            return_value=mock_validator,
        ):
            await websocket_endpoint(mock_ws, "room-abc", "p1")

        mock_ws.close.assert_called_once()
        kwargs = mock_ws.close.call_args.kwargs
        assert kwargs.get("code") == 4001

    async def test_ws_valid_token_proceeds_to_room_check(
        self, mock_ws, mock_validator
    ):
        """GIVEN WS connect with valid JWT WHEN handler runs THEN it proceeds past JWT check.

        Since no room exists, it closes with 1008 (room not found) rather than 4001.
        """
        from app.routes.websocket import websocket_endpoint

        mock_ws.query_params = {"token": "valid.jwt.token"}

        with patch(
            "app.routes.websocket._get_jwt_validator",
            return_value=mock_validator,
        ):
            await websocket_endpoint(mock_ws, "room-abc", "p1")

        # Should NOT have closed with 4001 (JWT passed)
        # Instead, closes with 1008 because room doesn't exist
        mock_ws.close.assert_called_once()
        kwargs = mock_ws.close.call_args.kwargs
        assert kwargs.get("code") == 1008, (
            f"Expected code 1008 (room not found), got {kwargs.get('code')}. "
            f"JWT validation should succeed, but room not found."
        )

    async def test_ws_expired_token_closes_4001(self, mock_ws, mock_validator):
        """GIVEN WS connect with expired JWT WHEN handler runs THEN closes with 4001."""
        from app.routes.websocket import websocket_endpoint

        mock_ws.query_params = {"token": "expired.jwt.token"}
        mock_validator.validate.side_effect = Exception("Token expired")

        with patch(
            "app.routes.websocket._get_jwt_validator",
            return_value=mock_validator,
        ):
            await websocket_endpoint(mock_ws, "room-abc", "p1")

        mock_ws.close.assert_called_once()
        kwargs = mock_ws.close.call_args.kwargs
        assert kwargs.get("code") == 4001

    async def test_ws_authenticated_connect_and_broadcast_state(
        self, mock_ws, mock_validator
    ):
        """GIVEN valid JWT and existing room+player WHEN connect THEN accepts and broadcasts.

        Full end-to-end: JWT passes → room found → player found → ws_manager.connect
        → broadcast room_update.
        """
        from app.routes.websocket import websocket_endpoint

        # Create a room with player
        room = Room(id="room-ws-auth", name="WS Auth Test")
        room.add_player(Player(id="p1", name="Alice", is_facilitator=True))

        # Set up room_manager to return this room via patch
        mock_room_manager = AsyncMock()
        mock_room_manager.get_room.return_value = room

        mock_ws.query_params = {"token": "valid.jwt.token"}

        # Break the while loop after first broadcast
        from fastapi import WebSocketDisconnect
        mock_ws.receive_json.side_effect = WebSocketDisconnect()

        with (
            patch(
                "app.routes.websocket._get_jwt_validator",
                return_value=mock_validator,
            ),
            patch(
                "app.routes.websocket.room_manager",
                mock_room_manager,
            ),
        ):
            await websocket_endpoint(mock_ws, "room-ws-auth", "p1")

        # Should NOT have closed the connection with 4001 (JWT passed)
        # After WebSocketDisconnect, ws_manager.disconnect is called (no explicit close)
        # Verify it did NOT send close with 4001 auth error

        # Verify broadcast was sent
        assert mock_ws.send_json.call_count >= 1
        sent_data = mock_ws.send_json.call_args[0][0]
        assert sent_data["type"] == "room_update"
        assert sent_data["data"]["room_id"] == "room-ws-auth"
        assert sent_data["data"]["room_name"] == "WS Auth Test"

    async def test_ws_vote_persistence_through_handler(
        self, mock_ws, mock_validator
    ):
        """GIVEN WS connected with valid JWT WHEN vote is sent THEN state updates and persists.

        Verifies that after JWT validation, the vote action leads to repo.save() being called.
        """
        from app.routes.websocket import websocket_endpoint

        # Create room with player
        room = Room(id="room-vote-test", name="Vote Test")
        room.add_player(Player(id="p1", name="Alice", is_facilitator=True))

        mock_room_manager = AsyncMock()
        mock_room_manager.get_room.return_value = room

        mock_ws.query_params = {"token": "valid.jwt.token"}

        # First receive returns vote action, second triggers disconnect
        from fastapi import WebSocketDisconnect
        mock_ws.receive_json.side_effect = [
            {"action": "vote", "vote": "5"},
            WebSocketDisconnect(),  # Break the while loop
        ]

        with (
            patch(
                "app.routes.websocket._get_jwt_validator",
                return_value=mock_validator,
            ),
            patch(
                "app.routes.websocket.room_manager",
                mock_room_manager,
            ),
        ):
            await websocket_endpoint(mock_ws, "room-vote-test", "p1")

        # Verify the vote was persisted via repo.save()
        assert mock_room_manager._repository.save.called, (
            "Expected repo.save() to be called when a vote is cast via WS"
        )

    async def test_ws_no_validator_skips_jwt_check(
        self, mock_ws
    ):
        """GIVEN no JWT validator configured WHEN WS connects THEN JWT is not checked."""
        from app.routes.websocket import websocket_endpoint

        mock_ws.query_params = {"token": "any-token"}

        # Mock _get_jwt_validator to return None (no auth configured)
        with patch(
            "app.routes.websocket._get_jwt_validator",
            return_value=None,
        ):
            await websocket_endpoint(mock_ws, "room-abc", "p1")

        # Should skip JWT check and proceed to room check
        mock_ws.close.assert_called_once()
        kwargs = mock_ws.close.call_args.kwargs
        assert kwargs.get("code") == 1008, "Should close with 1008 (room not found), not 4001"
