import uuid

from sqlalchemy import TypeDecorator, CHAR, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class GUID(TypeDecorator):
    """Platform-agnostic UUID type."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return str(value)


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def init_database(database_url: str):
    global _engine, _session_factory

    connect_args = {}
    pool_kwargs = {}

    if "sqlite" in database_url:
        connect_args["check_same_thread"] = False
        from sqlalchemy.pool import StaticPool
        pool_kwargs["poolclass"] = StaticPool
    else:
        pool_kwargs["pool_size"] = 5
        pool_kwargs["max_overflow"] = 10
        pool_kwargs["pool_pre_ping"] = True

    _engine = create_async_engine(
        database_url,
        connect_args=connect_args,
        echo=False,
        **pool_kwargs,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def create_tables():
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
