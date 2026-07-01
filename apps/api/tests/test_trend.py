"""口碑指数 roll-up — the live weekly ``sentimentTrend`` / ``vs`` aggregation.

These cover the firehose-derived 口碑指数 series that fills the weekly "口碑与痛点
分析" panels. The offline round-trip (``live=False``) is untouched and still keeps
the seed series verbatim (guarded by ``test_pipeline``); here we exercise the
``live=True`` path with a hand-seeded firehose.
"""

from __future__ import annotations

from datetime import date, timedelta

from nintel.engine.trend import (
    _sentiment_index,
    _weekly_sentiment_series,
    normalize_dashboard,
)
from nintel.store.db import get_session, reset_db
from nintel.store.models import IntelItemRow


def test_sentiment_index_weighting_and_min_sample():
    # pos=1, neu=0.5, neg=0 over the sample.
    assert _sentiment_index({"pos": 4}) == 100
    assert _sentiment_index({"neg": 4}) == 0
    assert _sentiment_index({"neu": 4}) == 50
    assert _sentiment_index({"pos": 3, "neg": 1}) == 75
    assert _sentiment_index({"pos": 1, "neu": 2}) == round(100 * (1 + 1.0) / 3)  # 67
    # Below the min sample the point is withheld (None), not a noisy 0/100.
    assert _sentiment_index({"pos": 2}) is None
    assert _sentiment_index({}) is None


def _seed_firehose(rows: list[tuple[str, str, str, int]]) -> None:
    """Insert ``(date, subject, sentiment, count)`` batches into a clean firehose."""
    reset_db()
    session = get_session()
    try:
        n = 0
        for d_str, subject, sentiment, count in rows:
            for _ in range(count):
                n += 1
                session.add(
                    IntelItemRow(
                        content_hash=f"h{n:04d}",
                        item_id=f"i{n}",
                        subject=subject,
                        source="reddit",
                        source_tier="community",
                        category="",  # firehose carries no reliable category
                        omada_impact="neutral",
                        title=f"t{n}",
                        url=f"https://example.com/{n}",
                        date=d_str,
                        payload={"sentiment": sentiment},
                    )
                )
        session.commit()
    finally:
        session.close()


def test_weekly_sentiment_series_buckets_by_iso_week():
    as_of = date(2026, 3, 30)
    wk_b, wk_c = as_of - timedelta(days=7), as_of
    _seed_firehose(
        [
            # Week B: omada 2pos+2neu -> 75 ; unifi 1pos+3neg -> 25
            (wk_b.isoformat(), "omada_self", "pos", 2),
            (wk_b.isoformat(), "omada_self", "neu", 2),
            (wk_b.isoformat(), "competitor", "pos", 1),
            (wk_b.isoformat(), "competitor", "neg", 3),
            # Week C (current): omada 3pos+1neg -> 75 ; unifi 2pos+2neg -> 50
            (wk_c.isoformat(), "omada_self", "pos", 3),
            (wk_c.isoformat(), "omada_self", "neg", 1),
            (wk_c.isoformat(), "competitor", "pos", 2),
            (wk_c.isoformat(), "competitor", "neg", 2),
        ]
    )

    trend, vs = _weekly_sentiment_series(as_of)

    label_b = f"W{wk_b.isocalendar()[1]:02d}"
    label_c = f"W{wk_c.isocalendar()[1]:02d}"
    assert trend == [
        {"wk": label_b, "omada": 75, "unifi": 25},  # oldest-first
        {"wk": label_c, "omada": 75, "unifi": 50},
    ]
    # vs is the current ISO week's point.
    assert vs == {"omada": 75, "unifi": 50}


def test_weekly_sentiment_series_withholds_thin_pair_and_industry():
    as_of = date(2026, 3, 30)
    _seed_firehose(
        [
            # Current week: omada has a full sample, but competitor is below the
            # min (2 < 3) -> the whole pair is withheld (a line needs both sides).
            (as_of.isoformat(), "omada_self", "pos", 4),
            (as_of.isoformat(), "competitor", "neg", 2),
            # industry never feeds a口碑 line and must be ignored entirely.
            (as_of.isoformat(), "industry", "pos", 9),
        ]
    )

    trend, vs = _weekly_sentiment_series(as_of)

    assert trend == []  # thin competitor side -> no renderable point
    assert vs == {"omada": 0, "unifi": 0}


def test_normalize_dashboard_live_wires_series_and_keeps_pains_empty():
    as_of = date(2026, 3, 30)
    _seed_firehose(
        [
            (as_of.isoformat(), "omada_self", "pos", 4),
            (as_of.isoformat(), "competitor", "neg", 4),
        ]
    )

    dash = normalize_dashboard(
        {"vs": "not-a-dict", "sentimentTrend": "junk"},  # LLM drift is overwritten
        items=[],
        tally={"signals": 1, "threat": 1, "opp": 0, "neutral": 0},
        live=True,
        as_of=as_of,
    )

    assert dash["vs"] == {"omada": 100, "unifi": 0}
    assert dash["sentimentTrend"] == [
        {"wk": f"W{as_of.isocalendar()[1]:02d}", "omada": 100, "unifi": 0}
    ]
    # pains stays empty (no mechanical basis) and 环比 deltas stay null.
    assert dash["pains"] == []
    assert dash["signalsDelta"] is None


def test_normalize_dashboard_live_without_as_of_is_empty_but_valid():
    # A missing/unparseable report date must not crash — just no series.
    dash = normalize_dashboard(
        {}, items=[], tally={}, live=True, as_of=None
    )
    assert dash["sentimentTrend"] == []
    assert dash["vs"] == {"omada": 0, "unifi": 0}
    assert dash["pains"] == []
