"""Source connectors.

Three upstreams feed the engine (PRD §2, SOLUTION §8):

* **Source A — sentiment-monitor** (Notion): Reddit / YouTube posts with
  sentiment / relevance / switch_intent annotations  → :class:`SentimentMonitorReader`
* **Source B — UNIFI_CHANNELS** (Supabase): UniFi product_releases / blog /
  community / store rows  → :class:`SupabaseReader`
* **Source C — industry RSS**: Wi-Fi Alliance / IEEE etc.  → :class:`RssReader`

Each reader implements the :class:`Connector` protocol and yields raw source
rows (:class:`RawRow`). The real upstreams and their credentials are **not**
present in this environment, so the shipped readers are *fixture-backed*: they
derive raw rows from the canonical seed reports (split by ``provenance`` /
``source``). The public method signatures are exactly what a live reader would
expose (``fetch(since: date) -> list[RawRow]``), so swapping in a real
Supabase/Notion/RSS reader is a drop-in. See each module docstring for the live
mapping.

Switch via ``NINTEL_CONNECTOR_MODE`` (``fixture`` default | ``live``); ``live``
raises ``NotImplementedError`` with a clear message.
"""

from .base import Connector, RawRow, connector_mode_guard
from .rss import RssReader
from .sentiment_monitor import SentimentMonitorReader
from .supabase import SupabaseReader

__all__ = [
    "Connector",
    "RawRow",
    "connector_mode_guard",
    "SupabaseReader",
    "SentimentMonitorReader",
    "RssReader",
    "all_connectors",
]


def all_connectors() -> list[Connector]:
    """The full connector set, in ingest priority order (B, A, C)."""

    return [SupabaseReader(), SentimentMonitorReader(), RssReader()]
