"""Integration tests for auth middleware — real signed JWT with mocked JWKS.

Covers:
- 3.3 Auth middleware with TestClient — sign test JWT, verify 401/200
- POST/DELETE rooms require valid JWT
- GET rooms does NOT require auth
- /auth/* paths are NOT protected
- Invalid/expired JWT returns 401
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt as jose_jwt
from jose.constants import Algorithms

pytestmark = pytest.mark.asyncio


def _generate_rs256_keypair() -> tuple:
    """Generate a real RSA key pair for testing.

    Returns:
        Tuple of (private_key, public_numbers_dict).
    """
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import rsa

    import base64

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_numbers = private_key.public_key().public_numbers()

    def _int_to_base64url(num: int) -> str:
        num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder="big")
        return base64.urlsafe_b64encode(num_bytes).rstrip(b"=").decode("ascii")

    jwk_key = {
        "kty": "RSA",
        "use": "sig",
        "kid": "integration-test-key",
        "n": _int_to_base64url(public_numbers.n),
        "e": _int_to_base64url(public_numbers.e),
        "alg": "RS256",
    }

    return private_key, jwk_key


def _sign_test_jwt(payload: dict, private_key, kid: str = "integration-test-key") -> str:
    """Sign a JWT payload with the given private key."""
    return jose_jwt.encode(
        claims=payload,
        key=private_key,
        algorithm=Algorithms.RS256,
        headers={"kid": kid},
    )


@pytest.fixture(scope="module")
def rsa_keypair():
    """Generate one RSA key pair for the entire module."""
    return _generate_rs256_keypair()


@pytest.fixture
def app_with_real_jwt(rsa_keypair):
    """Create a test FastAPI app with a real JWKSValidator (JWKS fetch mocked).

    Uses a REAL RSA key pair for signing, with the JWKS fetch mocked to return
    the matching public key. This tests the actual JWT validation code path.
    """
    from fastapi import FastAPI, Request

    from app.infrastructure.auth.jwt_validator import (
        JWKSValidator,
        create_auth_middleware,
    )

    private_key, jwk_key = rsa_keypair

    # Create a validator and mock its JWKS fetch
    validator = JWKSValidator(
        supabase_url="https://test.supabase.co",
        anon_key="test-anon-key",
    )
    validator._fetch_jwks = AsyncMock(return_value={"keys": [jwk_key]})

    app = FastAPI()
    app.middleware("http")(create_auth_middleware(validator))

    # Test routes mirroring main app
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


@pytest.fixture
def async_client(app_with_real_jwt):
    """Async client for the test app with real JWT validation."""
    transport = ASGITransport(app=app_with_real_jwt)
    return AsyncClient(transport=transport, base_url="http://test")


class TestAuthIntegration:
    """Auth middleware integration tests with real signed JWTs."""

    async def test_post_rooms_without_token_returns_401(
        self, async_client, rsa_keypair
    ):
        """GIVEN no auth token WHEN POST /api/rooms THEN returns 401."""
        resp = await async_client.post("/api/rooms", json={"name": "Test"})
        assert resp.status_code == 401

    async def test_delete_rooms_without_token_returns_401(
        self, async_client, rsa_keypair
    ):
        """GIVEN no auth token WHEN DELETE /api/rooms/{id} THEN returns 401."""
        resp = await async_client.delete("/api/rooms/test123")
        assert resp.status_code == 401

    async def test_post_rooms_with_valid_jwt_returns_200(
        self, async_client, rsa_keypair
    ):
        """GIVEN a valid RSA256-signed JWT WHEN POST /api/rooms THEN returns 200."""
        import time

        private_key, _ = rsa_keypair
        now = int(time.time())
        payload = {
            "sub": "user-456",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": now + 3600,
            "iat": now,
        }
        token = _sign_test_jwt(payload, private_key)

        resp = await async_client.post(
            "/api/rooms",
            json={"name": "Test Room"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == "new-room"

    async def test_state_injects_user_sub_with_valid_jwt(
        self, async_client, rsa_keypair
    ):
        """GIVEN a valid JWT WHEN POST /api/rooms THEN request.state has user_sub."""
        import time

        private_key, _ = rsa_keypair
        now = int(time.time())
        payload = {
            "sub": "user-456",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": now + 3600,
            "iat": now,
        }
        token = _sign_test_jwt(payload, private_key)

        resp = await async_client.post(
            "/api/rooms",
            json={"name": "Test Room"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["user_sub"] == "user-456"

    async def test_get_rooms_without_token_succeeds(
        self, async_client, rsa_keypair
    ):
        """GIVEN no auth token WHEN GET /api/rooms THEN succeeds (read-only)."""
        resp = await async_client.get("/api/rooms")
        assert resp.status_code == 200

    async def test_auth_routes_are_not_protected(
        self, async_client, rsa_keypair
    ):
        """GIVEN no auth token WHEN POST /auth/register THEN succeeds (skipped)."""
        resp = await async_client.post("/auth/register")
        assert resp.status_code == 200

    async def test_auth_me_without_token_succeeds(
        self, async_client, rsa_keypair
    ):
        """GIVEN no auth token WHEN GET /auth/me THEN succeeds (skipped)."""
        resp = await async_client.get("/auth/me")
        assert resp.status_code == 200

    async def test_expired_jwt_returns_401(
        self, async_client, rsa_keypair
    ):
        """GIVEN an expired JWT WHEN POST /api/rooms THEN returns 401."""
        import time

        private_key, _ = rsa_keypair
        now = int(time.time())
        payload = {
            "sub": "user-456",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": now - 3600,  # Expired 1 hour ago
            "iat": now - 7200,
        }
        token = _sign_test_jwt(payload, private_key)

        resp = await async_client.post(
            "/api/rooms",
            json={"name": "Test Room"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    async def test_malformed_jwt_returns_401(
        self, async_client, rsa_keypair
    ):
        """GIVEN a malformed JWT WHEN POST /api/rooms THEN returns 401."""
        resp = await async_client.post(
            "/api/rooms",
            json={"name": "Test Room"},
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
        )
        assert resp.status_code == 401

    async def test_wrong_audience_jwt_returns_401(
        self, async_client, rsa_keypair
    ):
        """GIVEN a JWT with wrong audience WHEN POST /api/rooms THEN returns 401."""
        import time

        private_key, _ = rsa_keypair
        now = int(time.time())
        payload = {
            "sub": "user-456",
            "email": "test@example.com",
            "aud": "wrong-audience",
            "exp": now + 3600,
            "iat": now,
        }
        token = _sign_test_jwt(payload, private_key)

        resp = await async_client.post(
            "/api/rooms",
            json={"name": "Test Room"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
