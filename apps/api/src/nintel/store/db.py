"""Engine / session management for the SQLite store.

The engine is created lazily and cached against the resolved DB path so tests
can point ``NINTEL_DB_PATH`` at a tmp file and get an isolated database. The
data directory is created on demand.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from .models import Base


@lru_cache(maxsize=8)
def _engine_for(db_url: str) -> Engine:
    # check_same_thread=False so the FastAPI threadpool can share the engine.
    return create_engine(
        db_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
    )


def get_engine() -> Engine:
    settings = get_settings()
    db_path: Path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return _engine_for(settings.db_url)


@lru_cache(maxsize=8)
def _sessionmaker_for(db_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=_engine_for(db_url), expire_on_commit=False, future=True)


def get_session() -> Session:
    """Return a new ORM session bound to the configured database."""

    get_engine()  # ensure data dir + engine exist
    return _sessionmaker_for(get_settings().db_url)()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session context manager (commit on success, rollback on error)."""

    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables if they do not yet exist."""

    Base.metadata.create_all(get_engine())


def reset_db() -> None:
    """Drop and recreate all tables (used by tests and ``seed --reset``)."""

    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
