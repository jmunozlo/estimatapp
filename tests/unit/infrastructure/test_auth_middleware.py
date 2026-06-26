"""Tests for auth middleware — JWT validation on protected routes.

Covers:
- 401 on POST /api/rooms without Bearer token
- 401 on DELETE /api/rooms/{id} without Bearer token
- 200 on POST /api/rooms with valid Bearer token
- 200 on GET /api/rooms — no auth needed (read-only)
- Request.state.user_sub injected with valid JWT
- Middleware skips /auth/* paths
"""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.auth.jwt_validator import JWTClaims

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_validator():
    """Create a mock JWKSValidator that accepts any token."""
    validator = AsyncMock()
    validator.validate.return_value = JWTClaims(
        sub="user-123",
        email="test@example.com",
        aud="authenticated",
        exp=9999999999,
    )
    return validator


@pytest.fixture
def app_with_middleware(mock_validator):
    """Create a test FastAPI app with the auth middleware for testing."""
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    from app.infrastructure.auth.jwt_validator import create_auth_middleware

    app = FastAPI()

    # Register the auth middleware
    app.middleware("http")(create_auth_middleware(mock_validator))

    # Add test routes
    @app.post("/api/rooms")
    async def create_room(request: Request):
        user_sub = getattr(request.state, "user_sub", None)
        return {"id": "new-room", "user_sub": user_sub}

    @app.delete("/api/rooms/{room_id}")
    async def delete_room(request: Request, room_id: str):
        user_sub = getattr(request.state, "user_sub", None)
        return {"deleted": room_id, "user_sub": user_sub}

    @app.get("/api/rooms")
    async def list_rooms():
        return [{"id": "room-1"}]

    @app.get("/api/rooms/{room_id}")
    async def get_room(room_id: str):
        return {"id": room_id}

    @app.post("/auth/register")
    async def register():
        return {"ok": True}

    @app.get("/auth/me")
    async def auth_me():
        return {"user": "test"}

    return app


class TestAuthMiddleware:
    """Auth middleware protection behavior."""

    async def test_post_rooms_without_token_returns_401(self, app_with_middleware):
        """GIVEN no auth token WHEN POST /api/rooms THEN returns 401."""
        transport = ASGITransport(app=app_with_middleware)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/rooms", json={"name": "Test Room"})
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Invalid or expired token"

    async def test_delete_rooms_without_token_returns_401(self, app_with_middleware):
        """GIVEN no auth token WHEN DELETE /api/rooms/{id} THEN returns 401."""
        transport = ASGITransport(app=app_with_middleware)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete("/api/rooms/test123")
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Invalid or expired token"

    async def test_post_rooms_with_valid_token_returns_200(self, app_with_middleware):
        """GIVEN valid Bearer token WHEN POST /api/rooms THEN returns 200 with user info."""
        transport = ASGITransport(app=app_with_middleware)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/rooms",
                json={"name": "Test Room"},
                headers={"Authorization": "Bearer valid.jwt.token"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "new-room"

    async def test_get_rooms_without_token_succeeds(self, app_with_middleware):
        """GIVEN no auth token WHEN GET /api/rooms THEN succeeds (read-only)."""
        transport = ASGITransport(app=app_with_middleware)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/rooms")
            assert resp.status_code == 200
            assert len(resp.json()) == 1

    async def test_auth_routes_are_not_protected(self, app_with_middleware):
        """GIVEN no auth token WHEN POST /auth/register THEN succeeds (skipped)."""
        transport = ASGITransport(app=app_with_middleware)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/auth/register")
            assert resp.status_code == 200

    async def test_auth_me_without_token_succeeds(self, app_with_middleware):
        """GIVEN no auth token WHEN GET /auth/me THEN succeeds (skipped)."""
        transport = ASGITransport(app=app_with_middleware)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/auth/me")
            assert resp.status_code == 200

    async def test_state_injects_user_sub_with_valid_token(self, app_with_middleware, mock_validator):
        """GIVEN valid JWT WHEN POST /api/rooms THEN request.state has user_sub."""
        transport = ASGITransport(app=app_with_middleware)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/rooms",
                json={"name": "Test Room"},
                headers={"Authorization": "Bearer valid.jwt.token"},
            )
            assert resp.status_code == 200
            assert resp.json()["user_sub"] == "user-123"

    async def test_middleware_returns_401_on_invalid_token(self, app_with_middleware, mock_validator):
        """GIVEN an invalid JWT WHEN POST /api/rooms THEN returns 401."""
        mock_validator.validate.side_effect = Exception("Invalid token")

        transport = ASGITransport(app=app_with_middleware)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/rooms",
                json={"name": "Test Room"},
                headers={"Authorization": "Bearer invalid.jwt.token"},
            )
            assert resp.status_code == 401
