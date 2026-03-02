"""
Database connections for the standalone MCP server.

The MCP server runs as a separate process, so it creates its own connections.
Uses asyncpg (PostgreSQL) and motor (MongoDB) — same drivers as the main app.
"""
import os
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient

# Strip the SQLAlchemy dialect prefix so asyncpg can parse the URL directly
_raw_db_url = os.environ.get("DATABASE_URL", "")
PG_DSN = _raw_db_url.replace("postgresql+asyncpg://", "postgresql://")

MONGO_URL = os.environ.get("MONGODB_URL", "")


async def get_pg_connection() -> asyncpg.Connection:
    """Open a one-off asyncpg connection."""
    return await asyncpg.connect(PG_DSN)


def get_mongo_db():
    """Return a Motor async database handle."""
    client = AsyncIOMotorClient(MONGO_URL)
    return client.medhistory
