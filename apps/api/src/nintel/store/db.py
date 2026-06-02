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

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from .models import Base


@lru_cache(maxsize=8)
def _engine_for(db_url: str) -> Engine:
    # check_same_thread=False so the FastAPI threadpool can share the engine.
    engine = create_engine(
        db_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
    )
    if db_url.startswith("sqlite"):
        # WAL lets the API read concurrently while the scheduled pipeline writes
        # the same file; busy_timeout avoids "database is locked" under that
        # 1-2x/day dual-writer load. Set per-connection (idempotent).
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - driver glue
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.close()

    return engine


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
    """Create missing tables, then apply lightweight column migrations.

    ``create_all`` builds new tables (incl. ``item_reports`` / ``heat_snapshots``)
    but never ALTERs an existing one, so ``ensure_columns`` adds the lifecycle
    columns to a pre-existing ``intel_items`` and backfills them.
    """

    Base.metadata.create_all(get_engine())
    from .migrate import ensure_columns

    ensure_columns()


def reset_db() -> None:
    """Drop and recreate all tables (used by tests and ``seed --reset``)."""

    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
