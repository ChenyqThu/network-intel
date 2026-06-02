"""WS1a: lifecycle-state schema, new tables, and the idempotent SQLite migration.

These guard the persistence layer added for cross-day dedup / turning-point
re-surfacing. They do NOT change report output — the offline round-trip
(test_contract) and pipeline invariants (test_pipeline) must stay green.
"""

from __future__ import annotations

from sqlalchemy import select, text

from nintel.store.db import get_engine, get_session, reset_db
from nintel.store.migrate import ensure_columns
from nintel.store.models import HeatSnapshotRow, IntelItemRow, ItemReportRow
from nintel.store.seed import seed


def test_lifecycle_columns_default_after_seed():
    seed(reset=True)
    session = get_session()
    try:
        row = session.scalars(select(IntelItemRow)).first()
        assert row is not None
        # New lifecycle columns exist with sane defaults on a fresh seed.
        assert row.state == "new"
        assert row.report_count == 0
        assert row.peak_heat == 0.0
        assert row.last_heat == 0.0
        assert row.last_switch_intent is False
        assert row.last_reported_at is None
    finally:
        session.close()


def test_new_tables_exist_and_empty():
    seed(reset=True)
    session = get_session()
    try:
        assert session.scalars(select(ItemReportRow)).all() == []
        assert session.scalars(select(HeatSnapshotRow)).all() == []
    finally:
        session.close()


def test_ensure_columns_migrates_legacy_table_and_is_idempotent():
    # Start from a clean schema, then simulate a *legacy* intel_items table that
    # predates the lifecycle columns, with one row carrying engagement payload.
    reset_db()
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE intel_items"))
        conn.execute(
            text(
                "CREATE TABLE intel_items ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "content_hash VARCHAR(64) NOT NULL,"
                "item_id VARCHAR(64) NOT NULL,"
                "subject VARCHAR(32), source VARCHAR(32), source_tier VARCHAR(16),"
                "category VARCHAR(32), omada_impact VARCHAR(32),"
                "title TEXT, url TEXT, date VARCHAR(16), payload JSON, created_at DATETIME)"
            )
        )
        # Bind every value as a parameter — embedding the JSON payload inline
        # would make SQLAlchemy parse its ``"likes":10`` colons as bind params.
        conn.execute(
            text(
                "INSERT INTO intel_items "
                "(content_hash,item_id,subject,source,source_tier,category,"
                " omada_impact,title,url,date,payload) VALUES "
                "(:ch,:iid,:subj,:src,:tier,:cat,:imp,:title,:url,:date,:payload)"
            ),
            {
                "ch": "h1", "iid": "d1", "subj": "competitor", "src": "reddit",
                "tier": "community", "cat": "sentiment", "imp": "threat",
                "title": "T", "url": "http://x", "date": "2026-06-01",
                "payload": '{"metrics":{"likes":10,"comments":5},"sentiment":"neg"}',
            },
        )

    ensure_columns()
    ensure_columns()  # second call must be a no-op (idempotent)

    with engine.begin() as conn:
        cols = {r[1] for r in conn.execute(text("PRAGMA table_info(intel_items)")).all()}
        assert {
            "first_seen", "last_seen", "last_reported_at", "report_count",
            "peak_heat", "last_heat", "last_sentiment", "last_switch_intent", "state",
        } <= cols
        first_seen, last_seen, peak, last, sent, state, rc = conn.execute(
            text(
                "SELECT first_seen,last_seen,peak_heat,last_heat,last_sentiment,"
                "state,report_count FROM intel_items WHERE content_hash='h1'"
            )
        ).one()
        # Backfilled from the row's date + payload heat (likes+comments=15).
        assert first_seen == "2026-06-01" and last_seen == "2026-06-01"
        assert peak == 15.0 and last == 15.0
        assert sent == "neg"
        # ALTER defaults applied for the non-backfilled columns.
        assert state == "new" and rc == 0

    # Leave a clean full-schema DB for any later module.
    reset_db()
