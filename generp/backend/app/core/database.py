"""Async SQLAlchemy engine, session factory, and tenant schema utilities."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import text

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Metadata DB engine (schema: public)
# ---------------------------------------------------------------------------
engine: AsyncEngine = create_async_engine(
    settings.metadata_database_url,
    echo=settings.is_development,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, automatically closing on exit."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Tenant-scoped engine factory
# ---------------------------------------------------------------------------
_tenant_engines: dict[str, AsyncEngine] = {}


def get_tenant_engine(tenant_id: str) -> AsyncEngine:
    """
    Return (or create) a SQLAlchemy async engine that connects with
    ``search_path`` set to the tenant's schema.

    Engines are cached per tenant to reuse connection pools.
    """
    if tenant_id not in _tenant_engines:
        schema_name = _schema_name(tenant_id)
        # connect_args lets us set the search_path at the connection level
        tenant_engine = create_async_engine(
            settings.database_url,
            echo=settings.is_development,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"server_settings": {"search_path": schema_name}},
        )
        _tenant_engines[tenant_id] = tenant_engine
    return _tenant_engines[tenant_id]


def get_tenant_session_factory(tenant_id: str) -> async_sessionmaker[AsyncSession]:
    """Return an async session factory scoped to the tenant schema."""
    tenant_engine = get_tenant_engine(tenant_id)
    return async_sessionmaker(
        bind=tenant_engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# ---------------------------------------------------------------------------
# Schema provisioning
# ---------------------------------------------------------------------------
def _schema_name(tenant_id: str) -> str:
    """Return the PostgreSQL schema name for a given tenant UUID."""
    # Strip dashes to produce a valid identifier
    safe_id = tenant_id.replace("-", "_")
    return f"tenant_{safe_id}"


async def create_tenant_schema(tenant_id: str) -> str:
    """
    Create a PostgreSQL schema for the tenant if it does not exist yet.

    Returns the schema name that was created/confirmed.
    """
    schema = _schema_name(tenant_id)
    async with engine.begin() as conn:
        # Use parameterised identifier via format — schema names cannot be
        # passed as bind parameters, but we validate the input first.
        _validate_schema_name(schema)
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    return schema


async def drop_tenant_schema(tenant_id: str, cascade: bool = False) -> None:
    """
    Drop the tenant schema.  Use with extreme caution — this is irreversible.
    Only called explicitly during tenant deletion flows.
    """
    schema = _schema_name(tenant_id)
    _validate_schema_name(schema)
    cascade_sql = "CASCADE" if cascade else "RESTRICT"
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} {cascade_sql}"))

    # Remove cached engine
    if tenant_id in _tenant_engines:
        await _tenant_engines[tenant_id].dispose()
        del _tenant_engines[tenant_id]


def _validate_schema_name(name: str) -> None:
    """
    Ensure the schema name only contains safe characters to prevent SQL injection.
    Valid pattern: tenant_ followed by hex chars and underscores.
    """
    import re

    if not re.fullmatch(r"tenant_[a-f0-9_]+", name):
        raise ValueError(f"Invalid schema name generated: {name!r}")


# ---------------------------------------------------------------------------
# Tenant DB session dependency (for use in tenant-scoped API routes)
# ---------------------------------------------------------------------------
async def get_tenant_db(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session scoped to the tenant schema."""
    factory = get_tenant_session_factory(tenant_id)
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
