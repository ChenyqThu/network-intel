"""Seed the SQLite store from the canonical contract fixtures.

Loads the two full seed reports (daily + weekly) into the ``reports`` table and
their items into ``intel_items`` (deduped by content_hash). Idempotent — safe to
run repeatedly. The archive index (``archive.json``) drives ``/api/reports``;
the entries beyond the two full seeds are metadata-only (see the API layer).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from .db import init_db, session_scope
from .models import IntelItemRow, ReportRow

SEED_REPORT_IDS = ("2026-06-01-daily", "2026-W22-weekly")


def _load(report_id: str) -> dict[str, Any]:
    path: Path = get_settings().contract_dir / f"{report_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def seed(*, reset: bool = False) -> dict[str, int]:
    """Load the seed reports + items into the DB. Returns counts."""

    from ..engine.ingest import content_hash  # local import avoids import cycle

    if reset:
        from .db import reset_db

        reset_db()
    else:
        init_db()

    reports_written = 0
    items_written = 0

    with session_scope() as session:
        existing_reports = set(
            session.scalars(select(ReportRow.report_id)).all()
        )
        existing_hashes = set(
            session.scalars(select(IntelItemRow.content_hash)).all()
        )

        for rid in SEED_REPORT_IDS:
            doc = _load(rid)

            if rid not in existing_reports:
                session.add(
                    ReportRow(
                        report_id=doc["report_id"],
                        type=doc["type"],
                        date=doc["date"],
                        title=doc.get("title"),
                        payload=doc,
                    )
                )
                existing_reports.add(rid)
                reports_written += 1

            for item in doc["items"]:
                ch = content_hash(item["source"], item["url"], item["title"])
                if ch in existing_hashes:
                    continue
                existing_hashes.add(ch)
                session.add(
                    IntelItemRow(
                        content_hash=ch,
                        item_id=item["id"],
                        subject=item["subject"],
                        source=item["source"],
                        source_tier=item["source_tier"],
                        category=item["category"],
                        omada_impact=item["omada_impact"],
                        title=item["title"],
                        url=item["url"],
                        date=item["date"],
                        payload=item,
                    )
                )
                items_written += 1

    return {"reports": reports_written, "items": items_written}


if __name__ == "__main__":  # pragma: no cover - manual invocation
    counts = seed(reset=True)
    print(f"seeded: {counts['reports']} reports, {counts['items']} items")
