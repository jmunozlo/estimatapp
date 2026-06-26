"""JWT validation using Supabase JWKS.

Validates RS256 JWTs issued by Supabase Auth. Fetches the JWKS
key set from the Supabase project and caches it with a 1-hour TTL.
"""

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwk, jwt as jose_jwt
from jose.constants import Algorithms


@dataclass
class JWTClaims:
    """Decoded JWT claims after successful validation."""

    sub: str  # user_id (UUID)
    email: str | None = None
    aud: str = ""
    exp: int = 0
    team_id: str | None = None


class JWKSValidator:
    """Validates Supabase JWTs with cached JWKS.

    Fetches the JWKS from the Supabase JWKS endpoint on first use
    and caches it for ``CACHE_TTL`` seconds (default: 3600 = 1 hour).
    """

    CACHE_TTL = 3600  # 1 hour

    def __init__(self, supabase_url: str, anon_key: str) -> None:
        """Initialize the validator.

        Args:
            supabase_url: Base URL of the Supabase project
                (e.g. https://<project>.supabase.co).
            anon_key: Supabase anon/public key (used for audience validation).
        """
        self.supabase_url = supabase_url
        self.anon_key = anon_key
        self._jwks_cache: tuple[dict, float] | None = None  # (keys, fetched_at)

    async def _fetch_jwks(self) -> dict:
        """Fetch JWKS from Supabase with 1-hour TTL caching.

        Returns:
            The JWKS dict with a ``keys`` list.
        """
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cache[1]) < self.CACHE_TTL:
            return self._jwks_cache[0]

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
            )
            resp.raise_for_status()
            keys = resp.json()
            self._jwks_cache = (keys, now)
            return keys

    async def validate(self, token: str) -> JWTClaims:
        """Validate a JWT and return its claims.

        Args:
            token: The raw JWT string to validate.

        Returns:
            Decoded JWTClaims if validation succeeds.

        Raises:
            Exception: If the token is invalid, expired, or malformed.
        """
        keys = await self._fetch_jwks()
        unverified_header = jose_jwt.get_unverified_header(token)
        key = next(
            k for k in keys["keys"] if k["kid"] == unverified_header["kid"]
        )
        rsa_key = jwk.construct(key, algorithm=Algorithms.RS256)
        payload = jose_jwt.decode(
            token,
            rsa_key,
            algorithms=[Algorithms.RS256],
            audience="authenticated",
        )

        return JWTClaims(
            sub=payload["sub"],
            email=payload.get("email"),
            aud=payload["aud"],
            exp=payload["exp"],
        )


def create_auth_middleware(
    validator: JWKSValidator,
) -> Callable[[Request, Callable[[Request], Awaitable[Any]]], Awaitable[Any]]:
    """Create a FastAPI middleware function that validates JWTs on protected routes.

    Protects POST and DELETE on ``/api/rooms/*`` paths.
    Skips ``/auth/*`` paths (registration, login, logout).
    Returns 401 on missing, invalid, or expired JWT.
    Injects ``request.state.user_sub`` and ``request.state.user_email`` on success.
    """

    async def auth_middleware(request: Request, call_next: Callable[[Request], Awaitable[Any]]) -> Any:
        path = request.url.path

        # Skip auth routes (register, login, logout)
        if path.startswith("/auth/"):
            return await call_next(request)

        # Protect POST/DELETE on rooms endpoints
        if path.startswith("/api/rooms") and request.method in ("POST", "DELETE"):
            auth = request.headers.get("Authorization")
            if not auth or not auth.startswith("Bearer "):
                return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

            try:
                token = auth.removeprefix("Bearer ")
                claims = await validator.validate(token)
                request.state.user_sub = claims.sub
                request.state.user_email = claims.email
            except Exception:
                return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        return await call_next(request)

    return auth_middleware
