"""Source A — omada-sentiment-monitor (Reddit + YouTube), read from its SQLite.

The 舆情 system collects Reddit posts + YouTube videos, AI-scores them
(relevance / sentiment), and stores them in ``omada_monitor.db``. We read that
DB directly (DB, not Notion) — only the AI-kept rows (``status='notion_synced'``)
become intel signals. URLs are the real Reddit/YouTube links.

Offline (default / tests) it reconstructs provenance-``A`` rows from the seeds.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .base import RawRow, connector_mode_guard, seed_rows_for

_LIVE_HINT = (
    "A live reader reads the omada-sentiment-monitor SQLite "
    "(NINTEL_SENTIMENT_DB_PATH -> omada_monitor.db): posts + youtube_videos."
)

_SENTIMENT = {"positive": "pos", "negative": "neg", "neutral": "neu", "mixed": "neu"}


def map_reddit_row(row: dict[str, Any]) -> RawRow:
    """Map a ``posts`` row -> RawRow (pure; parity-tested)."""
    url = row.get("url") or ("https://www.reddit.com" + (row.get("permalink") or ""))
    title = row.get("title") or ""
    cu = row.get("created_utc")
    published = (
        datetime.fromtimestamp(float(cu), tz=timezone.utc).date().isoformat() if cu else ""
    )
    raw: dict[str, Any] = {
        "source": "reddit", "provenance": "A", "url": url, "title": title, "date": published,
        "source_domain": "reddit.com", "source_tier": "community",
        "metrics": {"likes": row.get("score"), "comments": row.get("num_comments")},
        "sentiment": _SENTIMENT.get(row.get("ai_sentiment_quick")),
        "relevance": row.get("ai_relevance_score"),
    }
    return RawRow(source="reddit", provenance="A", url=url, title=title, published=published, raw=raw)


def map_youtube_row(row: dict[str, Any]) -> RawRow:
    """Map a ``youtube_videos`` row -> RawRow (pure; parity-tested)."""
    url = row.get("url") or ""
    title = row.get("title") or ""
    published = str(row.get("published_at") or "")[:10]
    raw: dict[str, Any] = {
        "source": "youtube", "provenance": "A", "url": url, "title": title, "date": published,
        "source_domain": "youtube.com", "source_tier": "community",
        "metrics": {
            "views": row.get("view_count"),
            "likes": row.get("like_count"),
            "comments": row.get("comment_count"),
        },
        "sentiment": _SENTIMENT.get(row.get("ai_sentiment_quick")),
        "relevance": row.get("ai_relevance_score"),
    }
    return RawRow(source="youtube", provenance="A", url=url, title=title, published=published, raw=raw)


class SentimentMonitorReader:
    """Reader for the sentiment monitor (source A), SQLite-backed."""

    name = "sqlite:omada_sentiment"
    provenance = "A"

    def fetch(self, since: date) -> list[RawRow]:
        if connector_mode_guard(self.name, _LIVE_HINT, self.provenance):
            return [r for r in self._fetch_live(since) if r.date >= since]
        rows = seed_rows_for(provenances={"A"})
        return [r for r in rows if r.date >= since]

    def _fetch_live(self, since: date, *, limit_reddit: int = 200, limit_youtube: int = 100) -> list[RawRow]:
        import sqlite3

        from ..config import get_settings

        db_path = get_settings().sentiment_db_path
        if not db_path or not Path(db_path).exists():
            raise NotImplementedError(
                f"source A: sentiment DB not found ({db_path!r}). Set "
                f"NINTEL_SENTIMENT_DB_PATH to omada_monitor.db."
            )
        # Read-only; never write the monitor's DB.
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
