"""B1 recent-coverage digest builder (temporal de-dup context for curate)."""

from __future__ import annotations

from datetime import date

from nintel.engine import recent_coverage


def _patch(monkeypatch, index, docs):
    monkeypatch.setattr("nintel.api.repository.archive_index", lambda: index)
    monkeypatch.setattr("nintel.api.repository.get_report", lambda rid: docs.get(rid))


def test_digest_excludes_self_and_out_of_window(monkeypatch):
    index = [  # archive_index is newest-first
        {"id": "2026-06-03-daily", "date": "2026-06-03", "type": "daily"},  # self (as_of)
        {"id": "2026-06-02-daily", "date": "2026-06-02", "type": "daily"},  # in window
        {"id": "2026-05-20-daily", "date": "2026-05-20", "type": "daily"},  # > 8d back
    ]
    docs = {
        "2026-06-02-daily": {
            "insights": [
                {"subject": "competitor", "title": "UniFi U7 价格下调", "takeaway": "💡 关注"}
            ],
            "items": [{"title": "Reddit: U7 deal", "url": "http://u"}],
        },
    }
    _patch(monkeypatch, index, docs)

    out = recent_coverage.build_digest("daily", date(2026, 6, 3))

    assert out is not None
    assert [d["report_id"] for d in out] == ["2026-06-02-daily"]  # self + stale excluded
    rec = out[0]
    assert rec["insights"][0]["title"] == "UniFi U7 价格下调"
    assert rec["insights"][0]["takeaway"] == "💡 关注"
    assert rec["items"][0]["url"] == "http://u"


def test_weekly_digest_only_considers_weeklies(monkeypatch):
    index = [
        {"id": "2026-W22-weekly", "date": "2026-05-31", "type": "weekly"},
        {"id": "2026-05-30-daily", "date": "2026-05-30", "type": "daily"},
    ]
    docs = {
        "2026-W22-weekly": {"insights": [{"title": "Wi-Fi 7 渗透", "takeaway": "💡"}], "items": []},
        "2026-05-30-daily": {"insights": [{"title": "noise", "takeaway": "x"}], "items": []},
    }
    _patch(monkeypatch, index, docs)

    out = recent_coverage.build_digest("weekly", date(2026, 6, 7))

    assert [d["type"] for d in out] == ["weekly"]  # the daily is filtered out


def test_digest_none_when_nothing_recent(monkeypatch):
    _patch(monkeypatch, [], {})
    assert recent_coverage.build_digest("daily", date(2026, 6, 3)) is None


def test_digest_is_best_effort_on_archive_error(monkeypatch):
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr("nintel.api.repository.archive_index", boom)
    # A repository hiccup must never propagate — the build proceeds without it.
    assert recent_coverage.build_digest("daily", date(2026, 6, 3)) is None
