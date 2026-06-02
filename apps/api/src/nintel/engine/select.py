"""Selection stage (WS1): cross-day dedup + turning-point re-surfacing.

Runs after ingest, before classify, when the pipeline persists state. For each
ingested item it:

* records a heat snapshot and advances the item's "seen" state,
* decides eligibility — a **new** item (never reported) clears a noise floor, or
  a **previously-reported** item re-surfaces only on a turning point (heat spike,
  sentiment flip, or newly-true switch intent) and only after a cooldown.

The eligibility math (:func:`evaluate`) is a pure function, unit-tested without a
DB. ``select_for_report`` wraps it with the SQLite state I/O and ordering.

This influences the **LLM** curate path (which builds the report from the live
pool). The offline/fixture path ignores selection for content (it replays the
seed manifest), so report output stays byte-identical; only state is advanced.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select as sa_select

from ..config import Settings, get_settings
from .ingest import content_hash
from .trend import heat_score

# Reason tags (also drive the re-surface badge in curate).
REASON_NEW = "new"
REASON_HEAT = "resurface:heat"
REASON_SENTIMENT = "resurface:sentiment"
REASON_SWITCH = "resurface:switch"


@dataclass(frozen=True)
class Prior:
    """Lightweight snapshot of an item's stored state (DB-free, for testing)."""

    report_count: int
    last_reported_at: str | None
    last_heat: float
    last_sentiment: str | None
    last_switch_intent: bool


@dataclass(frozen=True)
class SelectConfig:
    heat_delta: int
    heat_ratio: float
    cooldown_days: int
    min_heat: int
    max_items_daily: int

    @classmethod
    def from_settings(cls, s: Settings) -> "SelectConfig":
        return cls(
            heat_delta=s.resurface_heat_delta,
            heat_ratio=s.resurface_heat_ratio,
            cooldown_days=s.resurface_cooldown_days,
            min_heat=s.select_min_heat,
            max_items_daily=s.select_max_items_daily,
        )


@dataclass(frozen=True)
class Decision:
    eligible: bool
    reason: str | None  # REASON_* or None


@dataclass(frozen=True)
class SelectionResult:
    items: list[dict]          # eligible items, ordered + capped
    reasons: dict[str, str]    # url -> reason (only re-surface reasons kept)


def _days_between(iso_date: str, as_of: date) -> int:
    try:
        prev = date.fromisoformat(iso_date)
    except (ValueError, TypeError):
        return 10**6  # unparyable -> treat as long ago (cooldown satisfied)
    return (as_of - prev).days


def evaluate(
    prior: Prior | None,
    *,
    heat: float,
    sentiment: str | None,
    switch_intent: bool,
    as_of: date,
    cfg: SelectConfig,
) -> Decision:
    """Pure eligibility decision for one item. No I/O."""

    is_new = prior is None or prior.report_count == 0
    if is_new:
        ok = heat >= cfg.min_heat
        return Decision(ok, REASON_NEW if ok else None)

    # Previously reported: gate on cooldown, then require a turning point.
    cooldown_ok = (
        prior.last_reported_at is None
        or _days_between(prior.last_reported_at, as_of) >= cfg.cooldown_days
    )
    if not cooldown_ok:
        return Decision(False, None)

    spiked = (heat - prior.last_heat) >= cfg.heat_delta or (
        prior.last_heat > 0 and heat >= cfg.heat_ratio * prior.last_heat
    )
    flip = (
        prior.last_sentiment in ("pos", "neg")
        and sentiment in ("pos", "neg")
        and prior.last_sentiment != sentiment
    )
    switch_now = (not prior.last_switch_intent) and bool(switch_intent)

    # Precedence: market-moving signals first.
    if switch_now:
        return Decision(True, REASON_SWITCH)
    if flip:
        return Decision(True, REASON_SENTIMENT)
    if spiked:
        return Decision(True, REASON_HEAT)
    return Decision(False, None)


def order_bucket(reason: str | None, item: dict) -> int:
    """Lower = surfaced higher. Turning points beat routine new items."""
    if reason in (REASON_SWITCH, REASON_SENTIMENT):
        return 0
    if reason == REASON_HEAT:
        return 1
    if item.get("omada_impact") in ("threat", "needs_fix") and item.get("signal_strength") == "high":
        return 2
    return 3


def select_for_report(
    items: list[dict],
    *,
    report_type: str,
    as_of: date,
) -> SelectionResult:
    """Advance per-item state, decide eligibility, order + cap the pool.

    Assumes ingest has already persisted the items (rows exist by content_hash);
    here we only update lifecycle state and snapshots.
    """

    cfg = SelectConfig.from_settings(get_settings())
    as_of_iso = as_of.isoformat()

    from ..store.db import session_scope
    from ..store.models import HeatSnapshotRow, IntelItemRow

    scored: list[tuple[dict, str | None, float]] = []
    with session_scope() as s:
        for it in items:
            ch = content_hash(it["source"], it["url"], it["title"])
            heat = float(heat_score(it))
            sentiment = it.get("sentiment")
            switch_intent = bool(it.get("switch_intent"))

            row = s.scalar(sa_select(IntelItemRow).where(IntelItemRow.content_hash == ch))
            prior = (
                Prior(
                    report_count=row.report_count or 0,
                    last_reported_at=row.last_reported_at,
                    last_heat=row.last_heat or 0.0,
                    last_sentiment=row.last_sentiment,
                    last_switch_intent=bool(row.last_switch_intent),
                )
                if row is not None
                else None
            )

            decision = evaluate(
                prior,
                heat=heat,
                sentiment=sentiment,
                switch_intent=switch_intent,
                as_of=as_of,
                cfg=cfg,
            )

            _upsert_snapshot(s, HeatSnapshotRow, ch, as_of_iso, heat, it, sentiment)

            if row is not None:
                if row.first_seen is None:
                    row.first_seen = as_of_iso
                row.last_seen = as_of_iso
                row.last_heat = heat
                row.peak_heat = max(row.peak_heat or 0.0, heat)
                row.last_sentiment = sentiment
                row.last_switch_intent = switch_intent
                if decision.reason and decision.reason.startswith("resurface"):
                    row.state = "resurfaced"

            if decision.eligible:
                scored.append((it, decision.reason, heat))

    scored.sort(key=lambda t: (order_bucket(t[1], t[0]), -t[2]))
    scored = scored[: cfg.max_items_daily]
    return SelectionResult(
        items=[t[0] for t in scored],
        reasons={t[0]["url"]: t[1] for t in scored if t[1] and t[1] != REASON_NEW},
    )


def _upsert_snapshot(session, HeatSnapshotRow, ch, observed_on, heat, item, sentiment) -> None:
    existing = session.scalar(
        sa_select(HeatSnapshotRow).where(
            HeatSnapshotRow.content_hash == ch,
            HeatSnapshotRow.observed_on == observed_on,
        )
    )
    metrics = item.get("metrics") or {}
    likes = int(metrics.get("likes") or 0)
    comments = int(metrics.get("comments") or 0)
    views = int(metrics.get("views") or 0)
    if existing is None:
        session.add(
            HeatSnapshotRow(
                content_hash=ch,
                observed_on=observed_on,
                heat=heat,
                likes=likes,
                comments=comments,
                views=views,
                sentiment=sentiment,
            )
        )
    else:
        existing.heat = heat
        existing.likes = likes
        existing.comments = comments
        existing.views = views
        existing.sentiment = sentiment
