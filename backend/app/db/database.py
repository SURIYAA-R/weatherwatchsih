"""
Async database engine and session factory for SQLite (local) and Supabase/PostgreSQL (cloud).
"""
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./weatherwatch.db")

# Clean up quotes or query params if present
DATABASE_URL = DATABASE_URL.strip('"').strip("'")
if "?pgbouncer=true" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("?pgbouncer=true", "")

# Supabase / Render connection strings start with postgresql:// or postgres://
# SQLAlchemy async requires postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
elif "postgresql" in DATABASE_URL or "asyncpg" in DATABASE_URL:
    # Supabase uses PgBouncer on port 6543, which requires statement_cache_size=0
    connect_args["statement_cache_size"] = 0

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    from app.models import report  # noqa: F401 – ensure models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
