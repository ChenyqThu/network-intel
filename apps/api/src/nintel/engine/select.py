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
from datetime import date, timedelta

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
    daily_window_days: int = 2
    weekly_window_days: int = 7
    # Wide coarse-pool cap fed to the Sonnet 精选 stage (live + LLM path).
    prefilter_max: int = 80

    @classmethod
    def from_settings(cls, s: Settings) -> "SelectConfig":
        return cls(
            heat_delta=s.resurface_heat_delta,
            heat_ratio=s.resurface_heat_ratio,
            cooldown_days=s.resurface_cooldown_days,
            min_heat=s.select_min_heat,
            max_items_daily=s.select_max_items_daily,
            daily_window_days=s.daily_window_days,
            weekly_window_days=s.weekly_window_days,
            prefilter_max=s.select_prefilter_max,
        )

    def window_days(self, report_type: str) -> int:
        return self.weekly_window_days if report_type == "weekly" else self.daily_window_days


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


def _norm_title(title: str | None) -> str:
    return " ".join((title or "").lower().split())


def _collapse_crossposts(items: list[dict]) -> list[dict]:
    """Collapse the same story duplicated across a source to one representative.

    The sentiment monitor captures a post cross-posted to several subreddits as
    distinct rows (different URLs → distinct ``content_hash``), so a report could
    otherwise show one story 2-3×. Keyed on (source, normalized title); the
    highest-engagement copy wins. Items without a title are left untouched.
    """
    best: dict[tuple, dict] = {}
    passthrough: list[dict] = []
    for it in items:
        nt = _norm_title(it.get("title"))
        if not nt:
            passthrough.append(it)
            continue
        key = (it.get("source"), nt)
        if key not in best or heat_score(it) > heat_score(best[key]):
            best[key] = it
    return list(best.values()) + passthrough


def is_fresh(item_date: str | None, as_of: date, window_days: int) -> bool:
    """Freshness gate: an item qualifies only if its publish date falls inside
    the report window — within ``window_days`` of ``as_of`` and not in the
    future. A missing/unparseable date is *not* provably fresh, so it's excluded
    (this is what stops months-old or undated rows from leaking into a daily).
    """

    if not item_date:
        return False
    try:
        d = date.fromisoformat(str(item_date)[:10])
    except (ValueError, TypeError):
        return False
    delta = (as_of - d).days
    return 0 <= delta < window_days


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
    window = cfg.window_days(report_type)

    # Freshness gate (the fix for stale content): only items whose publish date
    # falls inside the report window are candidates. Without this, an item that
    # was simply "never reported" counted as new regardless of age, so months-
    # old (even last-year) rows leaked into a daily. Stale/undated rows are
    # dropped here so they never reach select scoring, curate, or the report.
    # Deep-research (provenance G) items are *period syntheses* produced at run
    # time (after the week ends), so their run-date reads as "future" against a
    # backdated window — exempt them from the freshness gate (they're always
    # in-scope for the report being built). Everything else must be in-window.
    fresh_items = [
        it
        for it in items
        if it.get("provenance") == "G" or is_fresh(it.get("date"), as_of, window)
    ]
    if len(fresh_items) != len(items):
        import logging

        logging.getLogger(__name__).info(
            "select: freshness window=%dd dropped %d/%d stale items (as_of=%s type=%s)",
            window, len(items) - len(fresh_items), len(items), as_of_iso, report_type,
        )
    items = _collapse_crossposts(fresh_items)

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
    # Wide coarse pool (初筛) — the Sonnet 精选 stage value-selects from this; the
    # final report cap is enforced downstream (shortlist_max), not here.
    scored = _balance(scored, cfg.prefilter_max)
    return SelectionResult(
        items=[t[0] for t in scored],
        reasons={t[0]["url"]: t[1] for t in scored if t[1] and t[1] != REASON_NEW},
    )


_SUBJECT_ORDER = ("omada_self", "competitor", "industry")


def _balance(scored: list, limit: int) -> list:
    """Two-level fair selection.

    Round-robin across **subjects** first — so ``omada_self`` (our own sentiment,
    the report's namesake section) is always represented and not crowded out by
    high-engagement competitor chatter — then round-robin across **sources**
    within each subject so one source doesn't dominate. Heat order is preserved
    inside a (subject, source) group. This is what makes the ``omada_self``
    section populate whenever the monitor has Omada/TP-Link posts in window.
    """
    from collections import OrderedDict

    by_subj: "OrderedDict[str, list]" = OrderedDict()
    for t in scored:
        by_subj.setdefault(t[0].get("subject", "competitor"), []).append(t)
    # Order items within each subject by a source round-robin (full length).
    for subj in by_subj:
        by_subj[subj] = _balance_by_source(by_subj[subj], len(by_subj[subj]))
    order = [s for s in _SUBJECT_ORDER if s in by_subj]
    order += [s for s in by_subj if s not in order]
    out: list = []
    while len(out) < limit and any(by_subj.values()):
        for subj in order:
            if by_subj[subj]:
                out.append(by_subj[subj].pop(0))
                if len(out) >= limit:
                    break
    return out


def _balance_by_source(scored: list, limit: int) -> list:
    """Round-robin across sources so one high-engagement source (e.g. blog, with
    10k+ view counts) doesn't crowd out Reddit/community/RSS. Within a source,
    the existing priority/heat order is preserved."""
    from collections import OrderedDict

    by_src: "OrderedDict[str, list]" = OrderedDict()
    for t in scored:
        # Gemini deep-research (provenance G) shares source="rss" with industry
        # RSS (C); give it a distinct balance slot so it isn't crowded out.
        src = "gemini" if t[0].get("provenance") == "G" else t[0].get("source", "?")
        by_src.setdefault(src, []).append(t)
    out: list = []
    while len(out) < limit and any(by_src.values()):
        for src in list(by_src):
            if by_src[src]:
                out.append(by_src[src].pop(0))
                if len(out) >= limit:
                    break
    return out


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
