"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


def _is_sqlite(uri: str) -> bool:
    return uri.startswith("sqlite:")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    uri = settings.sqlalchemy_database_uri
    if _is_sqlite(uri):
        engine = create_engine(
            uri,
            future=True,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(
        uri,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, class_=Session)


class _LazyEngineProxy:
    def __getattr__(self, name: str):
        return getattr(get_engine(), name)

    def __repr__(self) -> str:
        return repr(get_engine())


class _LazySessionMaker:
    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(get_session_factory(), name)


engine = _LazyEngineProxy()
SessionLocal = _LazySessionMaker()


def reset_db_runtime() -> None:
    """Clear cached engine/session factory (tests / local smoke)."""
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
