"""Database configuration and connection management.

This module provides async database connection setup, session management,
and base model definitions for SQLAlchemy ORM.

Example:
    >>> from src.core.database import get_db
    >>> async with get_db() as db:
    ...     result = await db.execute(select(Booking))
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from src.core.config import get_settings

settings = get_settings()

# Naming convention for constraints (helps with alembic migrations)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)

# Create declarative base with custom metadata
Base = declarative_base(metadata=metadata)


def create_engine() -> AsyncEngine:
    """Create async database engine with configuration from settings.

    Returns:
        Configured async SQLAlchemy engine.

    Example:
        >>> engine = create_engine()
        >>> async with engine.begin() as conn:
        ...     await conn.run_sync(Base.metadata.create_all)
    """
    connect_args: dict[str, Any] = {}

    # SQLite-specific configuration
    if "sqlite" in settings.database_url:
        connect_args = {"check_same_thread": False}

    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    # PostgreSQL-specific configuration
    if "postgresql" in settings.database_url:
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=True,
        )

    return engine


# Create engine and session factory
engine = create_engine()
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session.

    This is a dependency function for FastAPI that provides a database
    session and ensures proper cleanup after request completion.

    Yields:
        AsyncSession: Database session for the request.

    Example:
        >>> from fastapi import Depends
        >>>
        >>> @app.get("/bookings")
        >>> async def get_bookings(db: AsyncSession = Depends(get_db)):
        ...     result = await db.execute(select(Booking))
        ...     return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database by creating all tables.

    This should be called on application startup to ensure all tables exist.
    In production, use Alembic migrations instead.

    Example:
        >>> import asyncio
        >>> asyncio.run(init_db())
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections.

    This should be called on application shutdown to properly close
    all database connections.

    Example:
        >>> import asyncio
        >>> asyncio.run(close_db())
    """
    await engine.dispose()
