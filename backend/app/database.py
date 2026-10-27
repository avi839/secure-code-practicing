"""
Database configuration and session management.

Async SQLAlchemy setup. SQLite (aiosqlite) is the default; PostgreSQL works
via ``postgresql+asyncpg://`` URLs.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

if settings.database_backend == "sqlite":
    _engine_kwargs = {"connect_args": {"timeout": 15}}
else:
    _engine_kwargs = {"pool_size": 10, "max_overflow": 20}

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    pool_pre_ping=True,
    **_engine_kwargs,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative base for models
Base = declarative_base()


async def init_db() -> None:
    """Create all tables (Alembic is not used; see README)."""
    import app.models  # noqa: F401  (register models on Base.metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session
    Yields an AsyncSession and ensures proper cleanup
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
