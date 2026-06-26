"""Tests for JWKSValidator — JWT validation with mock JWKS fetch.

Covers valid, expired, and malformed tokens.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.asyncio


class _MockResponse:
    """Simulate httpx response."""

    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def _rs256_token_and_jwk(payload: dict, kid: str = "test-key-1") -> tuple[str, dict]:
    """Generate an RS256 JWT and its corresponding JWK public key dict.

    Returns:
        Tuple of (signed_token: str, jwk_public_key: dict).
    """
    import base64

    from jose import jwt as jose_jwt
    from jose.constants import Algorithms

    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    # Generate a real RSA key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_numbers = private_key.public_key().public_numbers()

    def _int_to_base64url(num: int) -> str:
        """Convert an integer to base64url-encoded string (no padding)."""
        num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder="big")
        return base64.urlsafe_b64encode(num_bytes).rstrip(b"=").decode("ascii")

    # Format public key as JWK dict with base64url-encoded values
    jwk_key = {
        "kty": "RSA",
        "use": "sig",
        "kid": kid,
        "n": _int_to_base64url(public_numbers.n),
        "e": _int_to_base64url(public_numbers.e),
    }

    # Sign the payload using jose_jwt.encode
    token = jose_jwt.encode(
        claims=payload,
        key=private_key,
        algorithm=Algorithms.RS256,
        headers={"kid": kid},
    )

    return token, jwk_key


class TestJWKSValidatorValidate:
    """JWKSValidator.validate() behavior."""

    async def test_validate_with_mocked_jwks(self):
        """GIVEN a mocked JWKS fetch WHEN validate is called THEN it returns JWTClaims."""
        from app.infrastructure.auth.jwt_validator import JWKSValidator

        import time

        now = int(time.time())
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": now + 3600,
            "iat": now,
        }

        token, jwk_key = _rs256_token_and_jwk(payload)

        validator = JWKSValidator(
            supabase_url="https://test.supabase.co",
            anon_key="test-anon-key",
        )
        validator._fetch_jwks = AsyncMock(return_value={"keys": [jwk_key]})

        claims = await validator.validate(token)

        assert claims.sub == "user-123"
        assert claims.email == "test@example.com"
        assert claims.aud == "authenticated"
        assert claims.exp == now + 3600

    async def test_validate_malformed_token_raises(self):
        """GIVEN a malformed JWT WHEN validate is called THEN raises an error."""
        from app.infrastructure.auth.jwt_validator import JWKSValidator

        validator = JWKSValidator(
            supabase_url="https://test.supabase.co",
            anon_key="test-anon-key",
        )
        validator._fetch_jwks = AsyncMock(
            return_value={"keys": [{"kty": "RSA", "kid": "k1", "n": "x", "e": "AQAB"}]}
        )

        with pytest.raises(Exception):
            await validator.validate("not-a-valid-jwt")

    async def test_validate_empty_token_raises(self):
        """GIVEN an empty token WHEN validate is called THEN raises an error."""
        from app.infrastructure.auth.jwt_validator import JWKSValidator

        validator = JWKSValidator(
            supabase_url="https://test.supabase.co",
            anon_key="test-anon-key",
        )

        with pytest.raises(Exception):
            await validator.validate("")

    async def test_caches_jwks_and_reuses(self):
        """GIVEN JWKS is cached WHEN validate is called twice THEN HTTP fetch is called once."""
        from app.infrastructure.auth.jwt_validator import JWKSValidator

        import time

        now = int(time.time())
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": now + 3600,
            "iat": now,
        }

        token, jwk_key = _rs256_token_and_jwk(payload)

        validator = JWKSValidator(
            supabase_url="https://test.supabase.co",
            anon_key="test-anon-key",
        )
        # Mock the underlying HTTP call to test caching
        with patch(
            "app.infrastructure.auth.jwt_validator.httpx.AsyncClient.get",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = _MockResponse({"keys": [jwk_key]})

            claims1 = await validator.validate(token)
            assert claims1.sub == "user-123"

            # Second call should use cache, not HTTP
            claims2 = await validator.validate(token)
            assert claims2.sub == "user-123"

            # HTTP should only be called once due to caching
            assert mock_get.call_count == 1

    async def test_rejects_expired_token(self):
        """GIVEN an expired JWT WHEN validate is called THEN raises."""
        from app.infrastructure.auth.jwt_validator import JWKSValidator

        import time

        now = int(time.time())
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": now - 3600,  # Expired 1 hour ago
            "iat": now - 7200,
        }

        token, jwk_key = _rs256_token_and_jwk(payload)

        validator = JWKSValidator(
            supabase_url="https://test.supabase.co",
            anon_key="test-anon-key",
        )
        validator._fetch_jwks = AsyncMock(return_value={"keys": [jwk_key]})

        with pytest.raises(Exception, match="expired|Expired|Signature"):
            await validator.validate(token)
