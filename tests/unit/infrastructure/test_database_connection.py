"""Tests for app.infrastructure.database.connection — asyncpg pool lifecycle."""

from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.database.connection import close_pool, get_pool, init_pool, pool


class TestPoolInit:
    """Pool initialization and lifecycle."""

    async def test_init_pool_creates_pool(self):
        """GIVEN a DATABASE_URL WHEN init_pool is called THEN pool is created with correct params."""
        mock_pool = AsyncMock()
        with patch("app.infrastructure.database.connection.asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool) as mock_create:
            await init_pool(dsn="postgresql://user:pass@localhost:5432/testdb", min_size=3, max_size=8)

            mock_create.assert_awaited_once_with(
                "postgresql://user:pass@localhost:5432/testdb",
                min_size=3,
                max_size=8,
            )

    async def test_init_pool_sets_global_pool(self):
        """GIVEN init_pool is called WHEN completed THEN get_pool returns the pool."""
        mock_pool = AsyncMock()
        with patch("app.infrastructure.database.connection.asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool):
            await init_pool(dsn="postgresql://user:pass@localhost:5432/testdb")
            result = get_pool()
            assert result is mock_pool

    async def test_close_pool_closes_and_resets(self):
        """GIVEN a pool is initialized WHEN close_pool is called THEN pool is closed and reset."""
        mock_pool = AsyncMock()
        with patch("app.infrastructure.database.connection.asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool):
            await init_pool(dsn="postgresql://user:pass@localhost:5432/testdb")
            await close_pool()

            mock_pool.close.assert_awaited_once()
            # After close, the global pool should be None
            with pytest.raises(AssertionError, match="Pool not initialized"):
                get_pool()

    async def test_get_pool_raises_when_not_initialized(self):
        """GIVEN pool is None WHEN get_pool is called THEN raises AssertionError."""
        with patch("app.infrastructure.database.connection.pool", None):
            with pytest.raises(AssertionError, match="Pool not initialized"):
                get_pool()

    async def test_close_pool_is_idempotent_when_not_initialized(self):
        """GIVEN pool is None WHEN close_pool is called THEN no error is raised."""
        with patch("app.infrastructure.database.connection.pool", None):
            # Should not raise
            await close_pool()
