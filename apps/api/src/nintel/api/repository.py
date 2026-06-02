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
import re
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


# ArchiveTheme values the frontend chip set understands (types.ts). store /
# dashboard are sections, not themes, so they are filtered out.
_SECTION_THEMES = {"omada_self", "competitor", "sentiment", "industry"}
_CITE_RE = re.compile(r"\{\{cite:\d+\}\}")


def _themes_from_report(doc: dict[str, Any]) -> list[str]:
    """Derive ArchiveTheme list: section keys (∩ valid themes) + pricing /
    new_product inferred from item categories. Order-stable, deduped."""
    themes: list[str] = []
    seen: set[str] = set()
    for sec in doc.get("sections", []):
        key = sec.get("key")
        if key in _SECTION_THEMES and key not in seen:
            seen.add(key)
            themes.append(key)
    cats = {it.get("category") for it in doc.get("items", [])}
    for extra in ("pricing", "new_product"):
        if extra in cats and extra not in seen:
            seen.add(extra)
            themes.append(extra)
    return themes


def _entry_from_report(doc: dict[str, Any]) -> dict[str, Any]:
    """Build an ArchiveEntry from a full report payload (frontend shape)."""
    tally = doc.get("tally") or {}
    lead = doc.get("lead") or {}
    items = doc.get("items", [])
    excerpt = lead.get("strong") or _CITE_RE.sub("", lead.get("text", "")).strip()
    entry: dict[str, Any] = {
        "id": doc["report_id"],
        "type": doc["type"],
        "date": doc["date"],
        "title": doc.get("title") or doc["report_id"],
        "excerpt": excerpt,
        "signals": tally.get("signals", len(items)),
        "threats": tally.get("threat", 0),
        "opps": tally.get("opp", 0),
        "themes": _themes_from_report(doc),
    }
    if not items:
        entry["empty"] = True
    return entry


def archive_index() -> list[dict[str, Any]]:
    """Archive index = published DB reports ∪ static historical metadata.

    Derived live from the ``reports`` table so a freshly published report shows
    up immediately (no process restart, no ``archive.json`` edit). Static
    ``contract/archive.json`` entries whose id has no DB row (metadata-only
    history) are unioned in. Sorted newest-first. Intentionally uncached so
    ``publish()`` is reflected on the next request.
    """
    session = get_session()
    try:
        rows = session.scalars(select(ReportRow)).all()
        db_entries = [_entry_from_report(r.payload) for r in rows]
    finally:
        session.close()
    db_ids = {e["id"] for e in db_entries}

    path = get_settings().contract_dir / "archive.json"
    static = json.loads(path.read_text(encoding="utf-8")).get("reports", [])
    hist = [e for e in static if e["id"] not in db_ids]

    return sorted(db_entries + hist, key=lambda e: e["date"], reverse=True)


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
