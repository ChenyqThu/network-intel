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
    return out


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
