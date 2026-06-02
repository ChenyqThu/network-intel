"""SQLAlchemy 2.x ORM models for the nintel store.

Two tables back the engine and API:

* ``intel_items`` — the normalized, deduped signal stream (one row per unique
  ``content_hash``). The full contract item payload is kept verbatim in
  ``payload`` so the API can stream items without reconstructing them, while the
  promoted columns enable cheap filtering (subject/source/impact/date).
* ``reports`` — the published ``report.json`` documents (one row per report_id),
  with the full contract JSON in ``payload`` and a few denormalized columns for
  the archive index.

SQLite is the dev/offline backend (``data/nintel.db``); the schema is portable
to Postgres unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all nintel ORM models."""


class IntelItemRow(Base):
    """A normalized intelligence signal, deduped by ``content_hash``."""

    __tablename__ = "intel_items"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_intel_items_content_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Stable contract id within a report (e.g. "d1", "ws3"). Not globally unique
    # across reports, so it is not the PK.
    item_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Promoted, queryable columns (mirror the contract item).
    subject: Mapped[str] = mapped_column(String(32), index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    source_tier: Mapped[str] = mapped_column(String(16), index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    omada_impact: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    date: Mapped[str] = mapped_column(String(16), index=True)

    # Full contract item payload (lossless).
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<IntelItemRow {self.item_id} {self.subject}/{self.omada_impact}>"


class ReportRow(Base):
    """A published ``report.json`` document."""

    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(16), index=True)
    date: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full contract document (lossless).
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<ReportRow {self.report_id} ({self.type})>"
