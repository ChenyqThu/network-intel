"""Source B — UNIFI_CHANNELS Supabase reader.

Live behaviour
--------------
A live :class:`SupabaseReader` would connect to the ``UNIFI_CHANNELS`` Supabase
project (``SUPABASE_URL`` + service key) and union four tables:

* ``product_releases`` → ``source = unifi_release`` (community.ui.com/releases)
* ``blog``             → ``source = blog``          (blog.ui.com)
* ``community``        → ``source = unifi_community``(community.ui.com questions)
* ``store``            → ``source = unifi_store`` / ``unifi_product`` (store.ui.com)

i.e. roughly::

    rows = (
        supabase.table("product_releases").select("*").gte("published_at", since)
        .execute().data + ...
    )

and map each row to :class:`RawRow`. URL integrity (PRD §7.8.6) is preserved —
``community.ui.com`` URLs keep their full UUIDs, never truncated.

Offline (default) the reader reconstructs these rows from the provenance-``B``
items in the canonical seed reports.
"""

from __future__ import annotations

from datetime import date

from .base import RawRow, connector_mode_guard, seed_rows_for

_LIVE_HINT = (
    "A live reader would query the UNIFI_CHANNELS Supabase tables "
    "(product_releases / blog / community / store) via SUPABASE_URL + service key."
)


class SupabaseReader:
    """Fixture-backed reader for the UniFi official channels (source B)."""

    name = "supabase:unifi_channels"
    provenance = "B"

    def fetch(self, since: date) -> list[RawRow]:
        connector_mode_guard(self.name, _LIVE_HINT)
        rows = seed_rows_for(provenances={"B"})
        return [r for r in rows if r.date >= since]
