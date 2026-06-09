"""Pending → published review gate implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..contract import Report, validate_against_schema


def _ensure_dirs() -> tuple[Path, Path]:
    settings = get_settings()
    pending = settings.pending_dir
    published = settings.published_dir
    pending.mkdir(parents=True, exist_ok=True)
    published.mkdir(parents=True, exist_ok=True)
    return pending, published


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def submit(report: Report) -> Path:
    """Write a built report to ``pending/`` (manual) or publish it (auto).

    Returns the path the report ended up at (pending or published).
    """

    doc = report.dump()
    validate_against_schema(doc)  # never let an invalid report into the queue
    pending, _ = _ensure_dirs()

    if get_settings().review_mode == "auto":
        return publish(report.report_id, doc=doc)

    path = pending / f"{report.report_id}.json"
    _write_json(path, doc)
    return path


def approve(report_id: str) -> Path:
    """Move a pending report to ``published/`` and persist it to the DB."""

    pending, _ = _ensure_dirs()
    src = pending / f"{report_id}.json"
    if not src.exists():
        raise FileNotFoundError(f"no pending report: {report_id}")
    doc = json.loads(src.read_text(encoding="utf-8"))
    out = publish(report_id, doc=doc)
    src.unlink()
    return out


def reject(report_id: str) -> None:
    """Discard a pending report."""

    pending, _ = _ensure_dirs()
    src = pending / f"{report_id}.json"
    if src.exists():
        src.unlink()


def publish(report_id: str, *, doc: dict[str, Any]) -> Path:
    """Validate, write to ``published/`` and upsert into the ``reports`` table."""

    validate_against_schema(doc)
    _, published = _ensure_dirs()
    out = published / f"{report_id}.json"
    _write_json(out, doc)
    _upsert_db(doc)
    _record_reported(doc)
    # Index the just-published items into the RAG history collection so future
    # reports can detect "already covered" / turning points. No-op unless RAG is
    # enabled (default off), so tests and the offline path are unaffected.
    from ..engine import rag

    if rag.kb_enabled():  # pragma: no cover - requires RAG + LLM enabled
        rag.index_items(doc.get("items", []))
    _index_to_kos(doc)
    return out


def _index_to_kos(doc: dict[str, Any]) -> None:
    """Push the published report into kos as a page (auto-ingest).

    Best-effort: the report is already written to disk + DB before this runs, so
    a kos outage is logged (not silent) and never rolls back a published report.
    """
    settings = get_settings()
    if not settings.kos_publish:
        return
    from ..engine import gbrain

    if not gbrain.gbrain_configured():
        return
    try:
        gbrain.index_report(doc)
    except Exception:  # noqa: BLE001 - post-commit side effect must not fail publish
        import logging

        logging.getLogger(__name__).exception(
            "kos index failed for %s (report still published)", doc.get("report_id")
        )


def _record_reported(doc: dict[str, Any]) -> None:
    """Record that a published report surfaced its items.

    Writes the item↔report junction and advances each item's reported-state
    (``report_count`` / ``last_reported_at`` / ``state``) so cross-day dedup and
    the cooldown work. Tolerant of items not yet persisted in ``intel_items``
    (e.g. fixture builds) — the junction is still recorded. Idempotent per
    (content_hash, report_id).
    """
    from sqlalchemy import select as sa_select

    from ..engine.ingest import content_hash
    from ..store.db import session_scope
    from ..store.models import IntelItemRow, ItemReportRow

    rid = doc["report_id"]
    rdate = doc.get("date")
    with session_scope() as session:
        for it in doc.get("items", []):
            try:
                ch = content_hash(it["source"], it["url"], it["title"])
            except KeyError:
                continue
            existing = session.scalar(
                sa_select(ItemReportRow).where(
                    ItemReportRow.content_hash == ch,
                    ItemReportRow.report_id == rid,
                )
            )
            first_time = existing is None
            if first_time:
                session.add(
                    ItemReportRow(
                        content_hash=ch,
                        report_id=rid,
                        report_date=rdate,
                        cite_id=it.get("cite_id"),
                    )
                )
            row = session.scalar(
                sa_select(IntelItemRow).where(IntelItemRow.content_hash == ch)
            )
            if row is not None:
                if first_time:
                    row.report_count = (row.report_count or 0) + 1
                if rdate and (row.last_reported_at is None or rdate > row.last_reported_at):
                    row.last_reported_at = rdate
                row.state = "reported"


def _upsert_db(doc: dict[str, Any]) -> None:
    from ..store.db import session_scope
    from ..store.models import ReportRow

    with session_scope() as session:
        row = session.get(ReportRow, doc["report_id"])
        if row is None:
            session.add(
                ReportRow(
                    report_id=doc["report_id"],
                    type=doc["type"],
                    date=doc["date"],
                    title=doc.get("title"),
                    payload=doc,
                )
            )
        else:
            row.type = doc["type"]
            row.date = doc["date"]
            row.title = doc.get("title")
            row.payload = doc


def unpublish(report_id: str) -> Path:
    """Pull a published report back to ``pending/`` for re-review.

    The published file and DB row stay in place — the public site keeps serving
    the current version until the operator re-publishes (which overwrites via
    the normal :func:`publish` upsert). Refuses to clobber an existing pending
    draft for the same id.
    """

    pending, published = _ensure_dirs()
    src = published / f"{report_id}.json"
    if not src.exists():
        raise FileNotFoundError(f"no published report: {report_id}")
    out = pending / f"{report_id}.json"
    if out.exists():
        raise FileExistsError(f"pending draft already exists: {report_id}")
    doc = json.loads(src.read_text(encoding="utf-8"))
    _write_json(out, doc)
    return out


def list_pending() -> list[str]:
    pending, _ = _ensure_dirs()
    return sorted(p.stem for p in pending.glob("*.json"))


def list_published() -> list[str]:
    _, published = _ensure_dirs()
    return sorted(p.stem for p in published.glob("*.json"))


def load_published(report_id: str) -> dict[str, Any] | None:
    _, published = _ensure_dirs()
    path = published / f"{report_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
