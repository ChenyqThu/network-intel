"""Connector protocol + the raw-row shape shared by all readers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ..config import get_settings


@dataclass(slots=True)
class RawRow:
    """A raw, *un-normalized* row as emitted by an upstream source.

    This is intentionally loose — it mirrors what a Supabase row / Notion page /
    RSS entry actually looks like before the ingest stage maps it onto the
    :class:`~nintel.contract.IntelItem` schema. ``provenance`` (A/B/C/D) and
    ``source`` carry the routing info; ``raw`` is the source-native record.
    """

    source: str
    provenance: str
    url: str
    title: str
    published: str  # ISO date (YYYY-MM-DD)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def date(self) -> date:
        return date.fromisoformat(self.published)


@runtime_checkable
class Connector(Protocol):
    """The interface every source reader implements.

    A live reader (Supabase/Notion/RSS client) would expose exactly this
    ``fetch`` signature; the engine never depends on the concrete reader.
    """

    name: str
    provenance: str

    def fetch(self, since: date) -> list[RawRow]:
        """Return raw rows published on/after ``since`` (newest-first)."""
        ...


def connector_mode_guard(reader_name: str, live_hint: str, provenance: str) -> bool:
    """Decide fixture vs live for one reader (per-source).

    Returns ``True`` to use the live path, ``False`` for the fixture path. In
    ``live`` mode a source must be opted in via ``NINTEL_LIVE_SOURCES``; a source
    that isn't listed raises a clear ``NotImplementedError`` (a loud "live but
    unprovisioned" rather than a silent fixture fallback). This lets sources be
    enabled one at a time.
    """

    settings = get_settings()
    if settings.connector_mode != "live":
        return False
    if provenance in settings.live_sources:
        return True
    raise NotImplementedError(
        f"{reader_name}: NINTEL_CONNECTOR_MODE=live but source {provenance!r} is not "
        f"enabled. {live_hint} Add {provenance} to NINTEL_LIVE_SOURCES, or use "
        f"fixture mode (NINTEL_CONNECTOR_MODE=fixture)."
    )


def domain_of(url: str) -> str:
    """The host portion of a URL (for ``source_domain``)."""
    from urllib.parse import urlparse

    return urlparse(url).netloc


# ---------------------------------------------------------------------------
# Shared fixture source: the canonical seed reports.
# ---------------------------------------------------------------------------
@lru_cache(maxsize=4)
def _load_seed(report_id: str) -> dict[str, Any]:
    path: Path = get_settings().contract_dir / f"{report_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _seed_items() -> list[dict[str, Any]]:
    """All items from both canonical seeds, deduped by URL.

    The fixture readers reconstruct raw rows from the curated seed items. We
    union the daily + weekly seeds (deduping on URL so the EAP610 / SG2218
    items that appear in both are not double-counted) to give the connectors a
    realistic, content-rich raw stream.
    """

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for rid in ("2026-06-01-daily", "2026-W22-weekly"):
        for item in _load_seed(rid)["items"]:
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            out.append(item)
    return out


def seed_rows_for(provenances: set[str], sources: set[str] | None = None) -> list[RawRow]:
    """Build :class:`RawRow` objects from seed items matching the filters.

    ``raw`` carries the source-native fields a live reader would surface
    (metrics, sentiment annotations, badges, stage, …) so the ingest stage has
    everything it needs to reproduce the curated item.
    """

    rows: list[RawRow] = []
    for item in _seed_items():
        if item.get("provenance") not in provenances:
            continue
        if sources is not None and item["source"] not in sources:
            continue
        rows.append(
            RawRow(
                source=item["source"],
                provenance=item["provenance"],
                url=item["url"],
                title=item["title"],
                published=item["date"],
                raw=dict(item),
            )
        )
    rows.sort(key=lambda r: r.published, reverse=True)
    return rows
