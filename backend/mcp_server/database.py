"""
Database access for the in-process MCP server.

PostgreSQL: shared asyncpg pool, lazy-initialized on first use, closed on app shutdown.
MongoDB:    reuses the singleton Motor client from app.db.mongodb.
"""
from typing import Optional
import asyncpg

from app.core.config import settings
from app.db.mongodb import mongodb

_pool: Optional[asyncpg.Pool] = None


def _asyncpg_dsn() -> str:
    """SQLAlchemy URLs use the postgresql+asyncpg:// scheme; asyncpg wants plain postgresql://."""
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def get_pg_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(_asyncpg_dsn(), min_size=1, max_size=5)
    return _pool


async def close_pg_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_mongo_db():
    return mongodb
