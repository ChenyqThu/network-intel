"""Weekly 高频痛点 synthesis — theme tally + firehose fetch/filter wiring.

The clustering itself is a (network) Sonnet call, stubbed here; the engine's job
is to fetch the right UniFi-community sample, count *real* members per theme, and
drop thin/duplicate ones so every rendered number reflects real items.
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from nintel.engine import pains
from nintel.store.db import get_session, reset_db
from nintel.store.models import IntelItemRow


def test_tally_counts_dedupes_drops_thin_and_caps():
    # theme A claims 0-3; B overlaps on 3 (first-claim wins -> B gets 4,5 only ->
    # 2 < min 3 -> dropped); C is a clean 3.
    themes = [
        {"name": "漫游/粘滞", "members": [0, 1, 2, 3]},
        {"name": "订阅涨价", "members": [3, 4, 5]},
        {"name": "App 体验", "members": [6, 7, 8]},
        {"name": "空标题", "members": [9, 10, 11]},
    ]
    # blank name is dropped even with enough members.
    themes[3]["name"] = "   "
    out = pains._tally_themes(themes, n_items=12)
    assert out == [
        {"name": "漫游/粘滞", "count": 4, "of": 4},  # of == largest count
        {"name": "App 体验", "count": 3, "of": 4},
    ]


def test_tally_ignores_out_of_range_indices_and_caps_to_five():
    themes = [
        {"name": f"T{k}", "members": [3 * k, 3 * k + 1, 3 * k + 2, 999]}  # 999 out of range
        for k in range(6)  # six valid themes -> capped to five
    ]
    out = pains._tally_themes(themes, n_items=18)
    assert len(out) == 5
    assert all(r["count"] == 3 for r in out)  # the bogus 999 never counted


def test_tally_empty_when_no_theme_qualifies():
    assert pains._tally_themes([{"name": "x", "members": [0, 1]}], n_items=10) == []
    assert pains._tally_themes([], n_items=10) == []


def _seed(rows: list[dict]) -> None:
    reset_db()
    session = get_session()
    try:
        for n, r in enumerate(rows, 1):
            session.add(
                IntelItemRow(
                    content_hash=f"p{n:04d}",
                    item_id=f"i{n}",
                    subject=r["subject"],
                    source="reddit",
                    source_tier=r["tier"],
                    category="",
                    omada_impact="neutral",
                    title=r["title"],
                    url=f"https://x/{n}",
                    date=r["date"],
                    payload={"sentiment": r.get("sentiment")},
                )
            )
        session.commit()
    finally:
        session.close()


def test_build_pains_offline_returns_empty():
    # llm disabled -> no clustering, no firehose read.
    assert pains.build_pains(date(2026, 3, 30), settings=SimpleNamespace(llm_enabled=False)) == []


def test_build_pains_fetches_only_unifi_community_complaints(monkeypatch):
    as_of = date(2026, 3, 30)
    inwin = (as_of - timedelta(days=3)).isoformat()
    old = (as_of - timedelta(days=20)).isoformat()
    rows = [
        # 6 genuine UniFi-community complaints (kept)
        *[
            {"subject": "competitor", "tier": "community", "date": inwin,
             "title": f"unifi gripe {k}", "sentiment": s}
            for k, s in enumerate(["neg", "neg", "neu", None, "neg", "neu"])
        ],
        # decoys that MUST be filtered out:
        {"subject": "competitor", "tier": "community", "date": inwin, "title": "praise", "sentiment": "pos"},
        {"subject": "omada_self", "tier": "community", "date": inwin, "title": "our bug", "sentiment": "neg"},
        {"subject": "competitor", "tier": "official", "date": inwin, "title": "ubnt blog", "sentiment": "neg"},
        {"subject": "competitor", "tier": "community", "date": old, "title": "stale", "sentiment": "neg"},
    ]
    _seed(rows)

    captured = {}

    def fake_cluster(items):
        captured["n"] = len(items)
        half = len(items) // 2
        return [
            {"name": "漫游/粘滞", "members": list(range(half))},
            {"name": "订阅涨价", "members": list(range(half, len(items)))},
        ]

    monkeypatch.setattr("nintel.engine.llm.cluster_pains", fake_cluster)

    out = pains.build_pains(as_of, settings=SimpleNamespace(llm_enabled=True, weekly_window_days=7))

    assert captured["n"] == 6, "only the 6 in-window UniFi-community complaints should be sampled"
    assert {r["name"] for r in out} == {"漫游/粘滞", "订阅涨价"}
    assert sum(r["count"] for r in out) == 6
    assert all(r["of"] == max(x["count"] for x in out) for r in out)
