"""Connection pool lifecycle for asyncpg.

Manages a global asyncpg connection pool initialized at app startup
and closed on shutdown.
"""

import asyncpg

pool: asyncpg.Pool | None = None


async def init_pool(dsn: str, min_size: int = 5, max_size: int = 10) -> None:
    """Initialize the global connection pool.

    Args:
        dsn: PostgreSQL connection string (e.g. postgresql://user:pass@host:port/db).
        min_size: Minimum number of connections in the pool (default 5).
        max_size: Maximum number of connections in the pool (default 10).
    """
    global pool
    pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)


async def close_pool() -> None:
    """Close the global connection pool gracefully.

    Safe to call even if the pool was never initialized.
    """
    global pool
    if pool is not None:
        await pool.close()
        pool = None


def get_pool() -> asyncpg.Pool:
    """Return the global connection pool.

    Raises:
        AssertionError: If the pool has not been initialized via init_pool().
    """
    assert pool is not None, "Pool not initialized"
    return pool
