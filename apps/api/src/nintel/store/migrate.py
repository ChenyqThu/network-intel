"""Lightweight, idempotent SQLite migrations (no Alembic).

``Base.metadata.create_all`` handles brand-new *tables*; but it never ALTERs an
existing table. For lifecycle columns added to ``intel_items`` after a DB was
already created (e.g. the live dev DB), we introspect via ``PRAGMA table_info``
and ``ALTER TABLE ... ADD COLUMN`` the missing ones, then backfill their state
from each row's stored payload so re-surface detection behaves sanely on the
first real ingest. Safe to call on every ``init_db()``.
"""

from __future__ import annotations

import json

from sqlalchemy import text

from .db import get_engine

# column name -> SQLite ADD COLUMN type/default clause.
_INTEL_ITEM_COLUMNS: dict[str, str] = {
    "first_seen": "VARCHAR(16)",
    "last_seen": "VARCHAR(16)",
    "last_reported_at": "VARCHAR(16)",
    "report_count": "INTEGER NOT NULL DEFAULT 0",
    "peak_heat": "FLOAT NOT NULL DEFAULT 0",
    "last_heat": "FLOAT NOT NULL DEFAULT 0",
    "last_sentiment": "VARCHAR(8)",
    "last_switch_intent": "BOOLEAN NOT NULL DEFAULT 0",
    "state": "VARCHAR(16) NOT NULL DEFAULT 'new'",
}


def ensure_columns() -> None:
    """Add any missing ``intel_items`` lifecycle columns, then backfill them.

    Idempotent: a no-op once the columns exist. Only meaningful for SQLite; on
    other dialects schema is managed elsewhere.
    """

    engine = get_engine()
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).all()
        }
        # Fresh DBs get the full schema from create_all (run before this); only
        # a pre-existing table can be missing the new columns.
        if "intel_items" not in tables:
            return

        have = {r[1] for r in conn.execute(text("PRAGMA table_info(intel_items)")).all()}
        added = [c for c in _INTEL_ITEM_COLUMNS if c not in have]
        for col in added:
            conn.execute(
                text(f"ALTER TABLE intel_items ADD COLUMN {col} {_INTEL_ITEM_COLUMNS[col]}")
            )
        if added:
            _backfill(conn)


def _backfill(conn) -> None:
    """Seed lifecycle state for rows that predate the new columns.

    ``first_seen``/``last_seen`` <- the row's ``date``; ``peak_heat``/``last_heat``
    <- heat derived from the stored payload; ``last_sentiment`` <- payload
    sentiment. Without this, every legacy row would look brand-new (and a heat
    ratio from 0 would falsely register as a spike). Only fills rows whose
    ``first_seen`` is still NULL, so it is safe to re-run.
    """

    # Imported lazily to avoid a store -> engine import cycle at module load.
    from ..engine.trend import heat_score

    rows = conn.execute(
        text("SELECT id, date, payload FROM intel_items WHERE first_seen IS NULL")
    ).all()
    for row_id, row_date, payload in rows:
        doc = payload if isinstance(payload, dict) else json.loads(payload)
        heat = float(heat_score(doc))
        conn.execute(
            text(
                "UPDATE intel_items SET first_seen=:d, last_seen=:d, "
                "peak_heat=:h, last_heat=:h, last_sentiment=:s WHERE id=:id"
            ),
            {"d": row_date, "h": heat, "s": doc.get("sentiment"), "id": row_id},
        )
