"""Read-side data access for the API.

Reports are served from the ``reports`` table (seeded from the contract +
populated by the review gate on publish). If the DB is empty (e.g. a fresh
process that hasn't been seeded), we fall back to the canonical contract seeds
so the API is always demonstrable. The archive index comes from
``contract/archive.json``; entries beyond the two full seed reports are
metadata-only and have no full report (the API returns 404 for those, honestly).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..store.db import get_session
from ..store.models import ReportRow

FULL_REPORT_IDS = {"2026-06-01-daily", "2026-W22-weekly"}


@lru_cache(maxsize=8)
def _seed_doc(report_id: str) -> dict[str, Any] | None:
    # Only the two canonical full reports are served from the contract dir.
    # Gating on this allow-list prevents a crafted ``report_id`` (e.g.
    # ``report.schema`` or ``archive``) from reading other JSON files out of the
    # contract directory and returning them as if they were reports.
    if report_id not in FULL_REPORT_IDS:
        return None
    path: Path = get_settings().contract_dir / f"{report_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def archive_index() -> list[dict[str, Any]]:
    path = get_settings().contract_dir / "archive.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("reports", [])


def get_report(report_id: str) -> dict[str, Any] | None:
    """Return the full report doc for ``report_id``, or None if not available."""

    session = get_session()
    try:
        row = session.get(ReportRow, report_id)
        if row is not None:
            return row.payload
    finally:
        session.close()
    # Fallback to contract seed (only the two full reports exist there).
    return _seed_doc(report_id)


def latest_report(report_type: str) -> dict[str, Any] | None:
    """Return the newest report of ``report_type`` (by date)."""

    session = get_session()
    try:
        rows = session.scalars(
            select(ReportRow).where(ReportRow.type == report_type)
        ).all()
        if rows:
            newest = max(rows, key=lambda r: r.date)
            return newest.payload
    finally:
        session.close()

    # Fallback: pick the newest full seed of this type from the archive index.
    candidates = [
        r for r in archive_index()
        if r["type"] == report_type and r["id"] in FULL_REPORT_IDS
    ]
    if not candidates:
        return None
    newest = max(candidates, key=lambda r: r["date"])
    return _seed_doc(newest["id"])


def all_full_reports() -> list[dict[str, Any]]:
    """Every full report available (DB rows ∪ the two contract seeds)."""

    docs: dict[str, dict[str, Any]] = {}
    session = get_session()
    try:
        for row in session.scalars(select(ReportRow)).all():
            docs[row.report_id] = row.payload
    finally:
        session.close()
    for rid in FULL_REPORT_IDS:
        if rid not in docs:
            seed = _seed_doc(rid)
            if seed:
                docs[rid] = seed
    return list(docs.values())


def has_full_report(report_id: str) -> bool:
    return get_report(report_id) is not None
