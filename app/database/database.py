"""
Database configuration for the UKB API.

Key fixes applied for Azure App Service + Neon PostgreSQL:

1. SSL: Use ssl='require' string (not ssl.SSLContext) for asyncpg compatibility
   on Azure. The ssl_context approach with CERT_NONE can cause handshake failures
   on some Azure network paths; 'require' is the correct asyncpg keyword.

2. DATABASE_URL assertion: Replaced hard assert with a clear RuntimeError so
   startup failures produce a readable log message on Azure.

3. Pool settings: pool_pre_ping=True prevents "connection is closed" errors
   caused by Azure's idle connection reaping. pool_recycle=1800 avoids stale
   connections from Neon's serverless pooler.

4. Removed ssl_context (ssl.CERT_NONE) which was unnecessary and could mask
   certificate issues in production.
"""

import os
import logging
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger("ukbAPI.database")

# Load environment variables from .env (no-op if already set by the OS/Azure)
load_dotenv()

# Get DB URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Set it in Azure App Service > Configuration > Application Settings."
    )

# --- SSL Configuration ---
# asyncpg accepts the string 'require' to enforce SSL without needing a full
# ssl.SSLContext object. This is the most portable approach across platforms
# (local, Docker, Azure App Service, Azure Container Apps).
connect_args: dict = {
    "timeout": 90,           # Increase connection timeout for Neon cold start
    "command_timeout": 90,   # Add command timeout for long-running queries
}
if "sqlite" not in DATABASE_URL:
    connect_args["ssl"] = "require"

# --- Async Engine ---
# We use a very high pool_timeout and connection timeout to handle Neon cold starts.
# Neon can take up to 50-60 seconds to wake up from a cold state.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_size=3,         # Minimal pool size for serverless
    max_overflow=2,      # Minimal overflow
    pool_timeout=90,     # Wait up to 90s for a connection from the pool
    pool_recycle=1800,
    pool_pre_ping=True,
)

# --- SessionMaker ---
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# --- Declarative Base ---
Base = declarative_base()


# --- Dependency for FastAPI routes ---
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Export components
__all__ = ["engine", "AsyncSessionLocal", "Base", "get_async_db"]
