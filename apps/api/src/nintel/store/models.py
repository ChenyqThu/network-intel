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

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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

    # --- WS1 cross-day lifecycle / dedup state -------------------------------
    # All nullable/defaulted so pre-existing rows survive an ALTER (see
    # store/migrate.py) and the offline report round-trip stays byte-identical.
    first_seen: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    last_seen: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    last_reported_at: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    report_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    peak_heat: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    last_heat: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    last_sentiment: Mapped[str | None] = mapped_column(String(8), nullable=True)
    last_switch_intent: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    # new | reported | dormant | resurfaced
    state: Mapped[str] = mapped_column(
        String(16), index=True, default="new", server_default="new", nullable=False
    )

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


class ItemReportRow(Base):
    """Junction linking an item (by ``content_hash``) to a report that surfaced it.

    The previously-missing item↔report edge. Lets us answer "which reports
    included this item" and powers cross-day dedup (``last_reported_at`` /
    ``report_count`` on :class:`IntelItemRow`).
    """

    __tablename__ = "item_reports"
    __table_args__ = (
        UniqueConstraint("content_hash", "report_id", name="uq_item_report"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    report_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    report_date: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    cite_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<ItemReportRow {self.content_hash[:8]}@{self.report_id}>"


class HeatSnapshotRow(Base):
    """A per-day engagement snapshot for an item — the time series behind
    turning-point (heat-spike) detection and future trend charts."""

    __tablename__ = "heat_snapshots"
    __table_args__ = (
        UniqueConstraint("content_hash", "observed_on", name="uq_heat_obs"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    observed_on: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    heat: Mapped[float] = mapped_column(Float, default=0.0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    sentiment: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<HeatSnapshotRow {self.content_hash[:8]}@{self.observed_on} h={self.heat}>"
