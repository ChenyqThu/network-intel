"""WS1b: selection predicate, ordering, cite_id assignment, reported-state loop."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select as sa_select

from nintel.engine.curate import assign_cite_ids
from nintel.engine.ingest import content_hash
from nintel.engine.select import (
    REASON_HEAT,
    REASON_NEW,
    REASON_SENTIMENT,
    REASON_SWITCH,
    TIER_FRESH,
    TIER_RESURFACE,
    TIER_SLOWBURN,
    TIER_UNDATED,
    Prior,
    SelectConfig,
    evaluate,
    is_fresh,
    order_bucket,
    window_decision,
)

CFG = SelectConfig(heat_delta=50, heat_ratio=2.0, cooldown_days=3, min_heat=10, max_items_daily=12)
AS_OF = date(2026, 6, 10)


def _reported(last_reported_at, *, last_heat=10.0, last_sentiment="neu", switch=False):
    return Prior(
        report_count=1,
        last_reported_at=last_reported_at,
        last_heat=last_heat,
        last_sentiment=last_sentiment,
        last_switch_intent=switch,
    )


# --- pure eligibility predicate -------------------------------------------
def test_new_item_passes_floor():
    d = evaluate(None, heat=20, sentiment="neu", switch_intent=False, as_of=AS_OF, cfg=CFG)
    assert d.eligible and d.reason == REASON_NEW


def test_new_item_below_floor_rejected():
    d = evaluate(None, heat=5, sentiment=None, switch_intent=False, as_of=AS_OF, cfg=CFG)
    assert not d.eligible and d.reason is None


def test_reported_within_cooldown_excluded_even_when_hot():
    prior = _reported("2026-06-09")  # 1 day ago < cooldown 3
    d = evaluate(prior, heat=1000, sentiment="neg", switch_intent=True, as_of=AS_OF, cfg=CFG)
    assert not d.eligible


def test_resurface_on_heat_delta():
    d = evaluate(_reported("2026-06-01", last_heat=10), heat=70, sentiment="neu",
                 switch_intent=False, as_of=AS_OF, cfg=CFG)  # delta 60 >= 50
    assert d.eligible and d.reason == REASON_HEAT


def test_resurface_on_heat_ratio():
    d = evaluate(_reported("2026-06-01", last_heat=10), heat=25, sentiment="neu",
                 switch_intent=False, as_of=AS_OF, cfg=CFG)  # delta 15<50 but 25>=2x10
    assert d.eligible and d.reason == REASON_HEAT


def test_resurface_on_sentiment_flip():
    d = evaluate(_reported("2026-06-01", last_sentiment="pos"), heat=12, sentiment="neg",
                 switch_intent=False, as_of=AS_OF, cfg=CFG)
    assert d.eligible and d.reason == REASON_SENTIMENT


def test_switch_intent_takes_precedence():
    # spike + flip + switch all true -> switch wins.
    d = evaluate(_reported("2026-06-01", last_sentiment="pos"), heat=70, sentiment="neg",
                 switch_intent=True, as_of=AS_OF, cfg=CFG)
    assert d.eligible and d.reason == REASON_SWITCH


def test_reported_quiet_item_excluded():
    d = evaluate(_reported("2026-06-01"), heat=12, sentiment="neu",
                 switch_intent=False, as_of=AS_OF, cfg=CFG)  # delta 2, ratio 1.2, no flip/switch
    assert not d.eligible


# --- freshness window (the stale-content fix) -----------------------------
def test_fresh_within_daily_window():
    # daily window=2 -> as_of and the day before qualify.
    assert is_fresh("2026-06-01", date(2026, 6, 1), 2)      # same day
    assert is_fresh("2026-05-31", date(2026, 6, 1), 2)      # prior day


def test_stale_outside_daily_window_rejected():
    assert not is_fresh("2026-05-30", date(2026, 6, 1), 2)  # 2 days -> out
    assert not is_fresh("2025-07-30", date(2026, 6, 1), 2)  # ~10 months -> out


def test_future_dated_rejected():
    assert not is_fresh("2026-06-02", date(2026, 6, 1), 2)  # tomorrow -> out


def test_missing_or_unparseable_date_rejected():
    assert not is_fresh(None, date(2026, 6, 1), 2)
    assert not is_fresh("", date(2026, 6, 1), 2)
    assert not is_fresh("not-a-date", date(2026, 6, 1), 2)


def test_balance_guarantees_omada_self_representation():
    from nintel.engine.select import _balance

    # 10 high-heat competitor reddit posts + 2 low-heat omada_self posts.
    scored = []
    for i in range(10):
        scored.append(({"subject": "competitor", "source": "reddit", "url": f"c{i}"}, None, 1000.0 - i))
    scored.append(({"subject": "omada_self", "source": "reddit", "url": "o1"}, None, 5.0))
    scored.append(({"subject": "omada_self", "source": "youtube", "url": "o2"}, None, 3.0))
    out = _balance(scored, 12)
    subjects = [t[0]["subject"] for t in out]
    # omada_self must appear despite far lower heat (subject round-robin first)
    assert subjects.count("omada_self") == 2
    # and it's surfaced early, not buried at the end
    assert out[0][0]["subject"] == "omada_self"


def test_collapse_crossposts_keeps_highest_engagement():
    from nintel.engine.select import _collapse_crossposts

    items = [
        {"source": "reddit", "title": "ER707 DNS", "url": "u1", "metrics": {"comments": 2}},
        {"source": "reddit", "title": "ER707 DNS", "url": "u2", "metrics": {"comments": 9}},
        {"source": "reddit", "title": "Different post", "url": "u3", "metrics": {"comments": 1}},
        {"source": "youtube", "title": "ER707 DNS", "url": "u4", "metrics": {"views": 5}},
    ]
    out = _collapse_crossposts(items)
    urls = {it["url"] for it in out}
    assert "u2" in urls and "u1" not in urls      # cross-post collapsed, higher-heat kept
    assert "u3" in urls                            # distinct title kept
    assert "u4" in urls                            # same title, different source kept


def test_weekly_window_covers_iso_week():
    # weekly window=7, as_of = Sunday 2026-05-31 -> Mon..Sun (W22) qualify.
    for d in ("2026-05-25", "2026-05-28", "2026-05-31"):
        assert is_fresh(d, date(2026, 5, 31), 7)
    assert not is_fresh("2026-05-24", date(2026, 5, 31), 7)  # prior Sunday -> out


def test_order_bucket_precedence():
    hi = {"omada_impact": "threat", "signal_strength": "high"}
    assert order_bucket(REASON_SWITCH, {}) == 0
    assert order_bucket(REASON_SENTIMENT, {}) == 0
    assert order_bucket(REASON_HEAT, {}) == 1
    assert order_bucket(REASON_NEW, hi) == 2
    assert order_bucket(REASON_NEW, {}) == 3


def test_order_bucket_slowburn_is_lowest():
    # slow-burn / undated soft-passes sink below every routine bucket, even a
    # would-be turning point (they're "only if there's room" items).
    assert order_bucket(REASON_NEW, {}, slowburn=True) == 4
    assert order_bucket(REASON_SWITCH, {}, slowburn=True) == 4


# --- intake windowing (A1 slow-burn/re-surface revival + A2 undated soft-pass) ---
def test_window_fresh_within_window():
    keep, tier = window_decision(
        {"date": "2026-06-09"}, is_reported=False, as_of=AS_OF, window=3, intake=3
    )
    assert keep and tier == TIER_FRESH


def test_window_g_is_exempt_even_when_ancient():
    keep, tier = window_decision(
        {"provenance": "G", "date": "2020-01-01"},
        is_reported=False, as_of=AS_OF, window=3, intake=3,
    )
    assert keep and tier == TIER_FRESH


def test_window_reported_bypasses_date_gate():
    # Old publish date, but previously reported -> re-surface tier (evaluate()
    # still decides whether a turning point actually re-admits it). This is the
    # A-iii fix: re-surface used to be unreachable for out-of-window content.
    keep, tier = window_decision(
        {"date": "2026-05-01"}, is_reported=True, as_of=AS_OF, window=3, intake=3
    )
    assert keep and tier == TIER_RESURFACE


def test_window_undated_soft_passes():
    for bad in (None, "", "not-a-date"):
        keep, tier = window_decision(
            {"date": bad}, is_reported=False, as_of=AS_OF, window=3, intake=3
        )
        assert keep and tier == TIER_UNDATED


def test_window_slowburn_band_when_intake_widened():
    # window 3, intake 5 -> a 4-day-old first-capture item rides the slow-burn tier
    keep, tier = window_decision(
        {"date": "2026-06-06"}, is_reported=False, as_of=AS_OF, window=3, intake=5
    )
    assert keep and tier == TIER_SLOWBURN


def test_window_stale_and_future_dropped():
    stale, _ = window_decision(
        {"date": "2026-05-01"}, is_reported=False, as_of=AS_OF, window=3, intake=3
    )
    future, _ = window_decision(
        {"date": "2026-06-11"}, is_reported=False, as_of=AS_OF, window=3, intake=3
    )
    assert not stale and not future


def test_intake_days_defaults_to_window_else_widens():
    base = dict(heat_delta=50, heat_ratio=2.0, cooldown_days=3, min_heat=0,
                max_items_daily=12, daily_window_days=3, weekly_window_days=7)
    cfg = SelectConfig(**base)
    assert cfg.intake_days("daily") == 3 and cfg.intake_days("weekly") == 7
    wide = SelectConfig(**base, intake_window_days=5)
    assert wide.intake_days("daily") == 5      # widened
    assert wide.intake_days("weekly") == 7     # max(5, 7) — never below the window


# --- deterministic cite_id assignment -------------------------------------
def test_assign_cite_ids_bijection_and_remap():
    doc = {
        "items": [
            {"id": "b", "cite_id": 9, "title": "B", "source_domain": "x.com",
             "date": "2026-06-01", "url": "http://b", "source_tier": "community"},
            {"id": "a", "cite_id": 4, "title": "A", "source_domain": "y.com",
             "date": "2026-06-01", "url": "http://a", "source_tier": "official"},
        ],
        "sections": [{"key": "omada_self", "title": "S", "items": ["a", "b"]}],
        "lead": {"text": "see {{cite:4}} and {{cite:9}}", "cite_refs": [4, 9]},
        "strategy": None,
    }
    out = assign_cite_ids(doc)
    by_id = {it["id"]: it for it in out["items"]}
    # display order a,b -> 1,2
    assert by_id["a"]["cite_id"] == 1 and by_id["b"]["cite_id"] == 2
    assert [r["cite_id"] for r in out["references"]] == [1, 2]
    assert {r["url"] for r in out["references"]} == {"http://a", "http://b"}
    # placeholders + cite_refs remapped through old->new
    assert out["lead"]["text"] == "see {{cite:1}} and {{cite:2}}"
    assert out["lead"]["cite_refs"] == [1, 2]


# --- reported-state loop (publish -> dedup state) --------------------------
def test_publish_records_reported_state_idempotent():
    from nintel.api import repository
    from nintel.review.gate import publish
    from nintel.store.db import get_session
    from nintel.store.models import IntelItemRow, ItemReportRow
    from nintel.store.seed import seed

    seed(reset=True)  # populates intel_items with the seed report items
    doc = repository.get_report("2026-06-01-daily")
    publish("2026-06-01-daily", doc=doc)

    s = get_session()
    try:
        jr = s.scalars(
            sa_select(ItemReportRow).where(ItemReportRow.report_id == "2026-06-01-daily")
        ).all()
        assert len(jr) == len(doc["items"])  # one junction row per item
        it = doc["items"][0]
        ch = content_hash(it["source"], it["url"], it["title"])
        row = s.scalar(sa_select(IntelItemRow).where(IntelItemRow.content_hash == ch))
        assert row is not None
        assert row.report_count >= 1
        assert row.last_reported_at == doc["date"]
        assert row.state == "reported"
    finally:
        s.close()

    # Re-publishing must not duplicate junctions or double-count.
    publish("2026-06-01-daily", doc=doc)
    s = get_session()
    try:
        jr2 = s.scalars(
            sa_select(ItemReportRow).where(ItemReportRow.report_id == "2026-06-01-daily")
        ).all()
        assert len(jr2) == len(doc["items"])
    finally:
        s.close()
    seed(reset=True)  # leave a clean DB for later modules
