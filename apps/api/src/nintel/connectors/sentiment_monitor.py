"""Source A — omada-sentiment-monitor (Reddit + YouTube).

The 舆情 system collects Reddit posts + YouTube videos, AI-scores them
(relevance / sentiment / brand tags / switch-intent) and **syncs them to Notion
hourly via GitHub Actions**. Notion is the fresh canonical store; the local
``data/omada_monitor.db`` SQLite is only updated on *local* monitor runs and
goes stale otherwise. So we read from **Notion by default**
(``NINTEL_SENTIMENT_BACKEND=notion``), with the SQLite reader available as an
alternate backend.

Brand is **per item**, not per source: the monitor watches both Omada/TP-Link
(``primary_keywords``) and competitors (``competitor_keywords``). We therefore
derive ``subject`` from the AI brand tags — Omada/TP-Link → ``omada_self``,
otherwise → ``competitor`` — which is what lets these items populate the
report's ``omada_self`` section instead of all landing under ``competitor``.

Offline (default / tests) it reconstructs provenance-``A`` rows from the seeds.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .base import RawRow, connector_mode_guard, seed_rows_for

_LIVE_HINT = (
    "A live reader reads the omada-sentiment-monitor data — Notion "
    "(NOTION_TOKEN + NOTION_DATABASE_ID/NOTION_YOUTUBE_DATABASE_ID) by default, "
    "or the local omada_monitor.db SQLite (NINTEL_SENTIMENT_BACKEND=sqlite)."
)

# Notion 情感倾向 / SQLite ai_sentiment_quick -> contract sentiment.
_SENTIMENT = {
    "正面": "pos", "负面": "neg", "中性": "neu", "混合": "neu",
    "positive": "pos", "negative": "neg", "neutral": "neu", "mixed": "neu",
}

# Brand markers (word-boundary matched, so "eap" won't match "cheap"). If one
# appears in an item's AI brand tags / title, it's about *our* product
# (omada_self) — even in a comparison; otherwise it's competitor-focused.
_OMADA_RE = re.compile(
    r"\b(omada|tp-?link|archer|deco|eap\d*|tapo|er6\d{2}|er7\d{3})\b", re.IGNORECASE
)


def _subject_from_text(*chunks: Any) -> str:
    """omada_self if an Omada/TP-Link brand marker is present, else competitor.

    Pass the most reliable brand signals (the monitor's AI ``匹配关键词`` tags and
    the title) — not free-text AI summaries, which mention Omada in competitor
    comparisons and cause false positives.
    """
    blob = " ".join(
        " ".join(c) if isinstance(c, (list, tuple)) else str(c or "")
        for c in chunks
    )
    return "omada_self" if _OMADA_RE.search(blob) else "competitor"


def _base_impact(subject: str, sentiment: str | None) -> str:
    """A valid base ``omada_impact`` for the subject (curate/Opus refines it).

    Respects the subject→impact vocabulary so an item is never left invalid:
    omada_self complaints are needs_fix, praise is strength_confirm; for a
    competitor a negative post is our opportunity, a positive one a threat.
    """
    if subject == "omada_self":
        return {"neg": "needs_fix", "pos": "strength_confirm"}.get(sentiment, "feature_input")
    return {"neg": "opportunity", "pos": "threat"}.get(sentiment, "neutral")


# ---------------------------------------------------------------------------
# SQLite backend (local omada_monitor.db) — kept as an alternate / for parity.
# ---------------------------------------------------------------------------
def map_reddit_row(row: dict[str, Any]) -> RawRow:
    """Map a SQLite ``posts`` row -> RawRow (pure; parity-tested)."""
    url = row.get("url") or ("https://www.reddit.com" + (row.get("permalink") or ""))
    title = row.get("title") or ""
    cu = row.get("created_utc")
    published = (
        datetime.fromtimestamp(float(cu), tz=timezone.utc).date().isoformat() if cu else ""
    )
    sentiment = _SENTIMENT.get(row.get("ai_sentiment_quick"))
    subject = _subject_from_text(row.get("title"), row.get("subreddit"))
    raw: dict[str, Any] = {
        "source": "reddit", "provenance": "A", "url": url, "title": title, "date": published,
        "source_domain": "reddit.com", "source_tier": "community", "subject": subject,
        "omada_impact": _base_impact(subject, sentiment),
        "metrics": {"likes": row.get("score"), "comments": row.get("num_comments")},
        "sentiment": sentiment, "relevance": row.get("ai_relevance_score"),
    }
    return RawRow(source="reddit", provenance="A", url=url, title=title, published=published, raw=raw)


def map_youtube_row(row: dict[str, Any]) -> RawRow:
    """Map a SQLite ``youtube_videos`` row -> RawRow (pure; parity-tested)."""
    url = row.get("url") or ""
    title = row.get("title") or ""
    published = str(row.get("published_at") or "")[:10]
    sentiment = _SENTIMENT.get(row.get("ai_sentiment_quick"))
    subject = _subject_from_text(row.get("title"), row.get("channel_title"))
    raw: dict[str, Any] = {
        "source": "youtube", "provenance": "A", "url": url, "title": title, "date": published,
        "source_domain": "youtube.com", "source_tier": "community", "subject": subject,
        "omada_impact": _base_impact(subject, sentiment),
        "metrics": {
            "views": row.get("view_count"),
            "likes": row.get("like_count"),
            "comments": row.get("comment_count"),
        },
        "sentiment": sentiment, "relevance": row.get("ai_relevance_score"),
    }
    return RawRow(source="youtube", provenance="A", url=url, title=title, published=published, raw=raw)


# ---------------------------------------------------------------------------
# Notion backend (fresh canonical store) — property extractors + mappers.
# ---------------------------------------------------------------------------
def _np_text(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    t = prop.get("type")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in prop.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
    return ""


def _np_date(prop: dict[str, Any] | None) -> str:
    d = (prop or {}).get("date")
    return (d.get("start") or "")[:10] if d else ""


def _np_select(prop: dict[str, Any] | None) -> str | None:
    s = (prop or {}).get("select")
    return s.get("name") if s else None


def _np_multi(prop: dict[str, Any] | None) -> list[str]:
    return [o.get("name", "") for o in (prop or {}).get("multi_select", [])]


def _np_num(prop: dict[str, Any] | None):
    return (prop or {}).get("number")


def _np_check(prop: dict[str, Any] | None) -> bool:
    return bool((prop or {}).get("checkbox"))


def _np_url(prop: dict[str, Any] | None) -> str:
    return (prop or {}).get("url") or ""


def map_notion_reddit(page: dict[str, Any]) -> RawRow:
    """Map a Notion reddit page -> RawRow (pure; parity-tested)."""
    p = page.get("properties", {})
    url = _np_url(p.get("Reddit链接"))
    title = _np_text(p.get("标题"))
    published = _np_date(p.get("发布时间")) or _np_date(p.get("采集时间"))
    sentiment = _SENTIMENT.get(_np_select(p.get("情感倾向")))
    subject = _subject_from_text(_np_multi(p.get("匹配关键词")), _np_multi(p.get("产品型号")), title)
    raw: dict[str, Any] = {
        "source": "reddit", "provenance": "A", "url": url, "title": title, "date": published,
        "source_domain": "reddit.com", "source_tier": "community", "subject": subject,
        "omada_impact": _base_impact(subject, sentiment),
        "metrics": {"likes": _np_num(p.get("分数")), "comments": _np_num(p.get("评论数"))},
        "sentiment": sentiment, "relevance": _np_num(p.get("相关性得分")),
        "switch_intent": _np_check(p.get("切换意图")),
    }
    summary = _np_text(p.get("AI摘要")) or _np_text(p.get("核心主张"))
    if summary:
        raw["summary"] = summary
    return RawRow(source="reddit", provenance="A", url=url, title=title, published=published, raw=raw)


def map_notion_youtube(page: dict[str, Any]) -> RawRow:
    """Map a Notion youtube page -> RawRow (pure; parity-tested)."""
    p = page.get("properties", {})
    url = _np_url(p.get("视频链接"))
    title = _np_text(p.get("标题"))
    published = _np_date(p.get("发布时间")) or _np_date(p.get("采集时间"))
    sentiment = _SENTIMENT.get(_np_select(p.get("情感倾向")))
    # Title + topic only — NOT the AI summary (it mentions Omada in competitor
    # comparisons, which would mis-file UniFi videos under omada_self).
    subject = _subject_from_text(title, _np_select(p.get("主题分类")))
    raw: dict[str, Any] = {
        "source": "youtube", "provenance": "A", "url": url, "title": title, "date": published,
        "source_domain": "youtube.com", "source_tier": "community", "subject": subject,
        "omada_impact": _base_impact(subject, sentiment),
        "metrics": {
            "views": _np_num(p.get("播放量")),
            "likes": _np_num(p.get("点赞数")),
            "comments": _np_num(p.get("评论数")),
        },
        "sentiment": sentiment, "relevance": _np_num(p.get("相关性得分")),
    }
    summary = _np_text(p.get("AI摘要"))
    if summary:
        raw["summary"] = summary
    return RawRow(source="youtube", provenance="A", url=url, title=title, published=published, raw=raw)


def _notion_query(db_id: str, since: date, *, date_prop: str = "发布时间", page_cap: int = 300) -> list[dict[str, Any]]:  # pragma: no cover - network
    """Query a Notion database for rows published on/after ``since`` (newest first)."""
    token = os.environ["NOTION_TOKEN"]
    version = os.getenv("NOTION_API_VERSION", "2022-06-28")
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    while len(out) < page_cap:
        body: dict[str, Any] = {
            "page_size": 100,
            "filter": {"property": date_prop, "date": {"on_or_after": since.isoformat()}},
            "sorts": [{"property": date_prop, "direction": "descending"}],
        }
        if cursor:
            body["start_cursor"] = cursor
        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            data=json.dumps(body).encode("utf-8"), method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": version,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted host)
            data = json.loads(resp.read().decode("utf-8", "replace"))
        out.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return out


class SentimentMonitorReader:
    """Reader for the sentiment monitor (source A): Notion (default) or SQLite."""

    name = "sentiment:omada_monitor"
    provenance = "A"

    def fetch(self, since: date) -> list[RawRow]:
        if connector_mode_guard(self.name, _LIVE_HINT, self.provenance):
            rows = self._fetch_live(since)
        else:
            rows = seed_rows_for(provenances={"A"})
        # RawRow.date parses published; keep only valid, in-range rows.
        return [r for r in rows if r.published and r.date >= since]

    def _fetch_live(self, since: date) -> list[RawRow]:  # pragma: no cover - network
        from ..config import get_settings

        backend = (get_settings().sentiment_backend or "notion").lower()
        if backend == "sqlite":
            return self._fetch_sqlite(since)
        return self._fetch_notion(since)

    def _fetch_notion(self, since: date) -> list[RawRow]:  # pragma: no cover - network
        if not os.getenv("NOTION_TOKEN"):
            raise NotImplementedError(
                "source A (notion): NOTION_TOKEN not set. Set it + "
                "NOTION_DATABASE_ID / NOTION_YOUTUBE_DATABASE_ID, or use "
                "NINTEL_SENTIMENT_BACKEND=sqlite."
            )
        rows: list[RawRow] = []
        reddit_db = os.getenv("NOTION_DATABASE_ID")
        youtube_db = os.getenv("NOTION_YOUTUBE_DATABASE_ID")
        if reddit_db:
            for page in _notion_query(reddit_db, since):
                rr = map_notion_reddit(page)
                if rr.url and rr.title:
                    rows.append(rr)
        if youtube_db:
            for page in _notion_query(youtube_db, since):
                rr = map_notion_youtube(page)
                if rr.url and rr.title:
                    rows.append(rr)
        return rows

    def _fetch_sqlite(self, since: date, *, limit_reddit: int = 200, limit_youtube: int = 100) -> list[RawRow]:  # pragma: no cover - sqlite
        import sqlite3

        from ..config import get_settings

        db_path = get_settings().sentiment_db_path
        if not db_path or not Path(db_path).exists():
            raise NotImplementedError(
                f"source A (sqlite): DB not found ({db_path!r}). Set "
                f"NINTEL_SENTIMENT_DB_PATH to omada_monitor.db."
            )
        conn = sqlite3.connect(f"file:{os.fspath(db_path)}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows: list[RawRow] = []
            for r in conn.execute(
                "SELECT subreddit,title,permalink,url,score,num_comments,created_utc,"
                "ai_relevance_score,ai_sentiment_quick FROM posts "
                "WHERE status='notion_synced' ORDER BY created_utc DESC LIMIT ?",
                (limit_reddit,),
            ):
                rows.append(map_reddit_row(dict(r)))
            for r in conn.execute(
                "SELECT channel_title,title,url,published_at,view_count,like_count,"
                "comment_count,ai_relevance_score,ai_sentiment_quick FROM youtube_videos "
                "WHERE status='notion_synced' ORDER BY published_at DESC LIMIT ?",
                (limit_youtube,),
            ):
                rows.append(map_youtube_row(dict(r)))
            return rows
        finally:
            conn.close()
