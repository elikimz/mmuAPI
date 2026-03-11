
import ssl
import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables
load_dotenv()

# Get DB URL
DATABASE_URL = os.getenv("DATABASE_URL")
assert DATABASE_URL is not None, "❌ DATABASE_URL not loaded from .env"

# --- SSL Context ---
# Required for cloud databases like Neon, Supabase, and Azure PostgreSQL
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# --- Async Engine ---
# Added pooling settings to prevent "connection is closed" errors on Azure
# Determine if SSL is needed (Postgres usually needs it, SQLite does not)
connect_args = {}
if "sqlite" not in DATABASE_URL:
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to False in production
    connect_args=connect_args,
    pool_size=20,          # Max number of persistent connections
    max_overflow=10,       # Max connections allowed beyond pool_size
    pool_timeout=30,       # Seconds to wait before giving up on getting a connection
    pool_recycle=1800,     # Recycle connections every 30 minutes to prevent stale links
    pool_pre_ping=True     # Check if connection is alive before using it
)

# --- SessionMaker ---
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevents attributes from expiring after commit
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
