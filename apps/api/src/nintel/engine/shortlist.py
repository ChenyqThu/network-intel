"""Shortlist stage (Sonnet tier) — value-based 精选.

Python ``select`` casts a wide rule-based net (初筛: freshness / dedup /
turning-point / balance). This stage hands that coarse pool to **Sonnet** with an
editorial system prompt (background / goal / filtering strategy) and keeps only
the most *decision-relevant* items (精选). Sonnet **selects real items by index**
— it never generates content, so the NO-FABRICATION rule holds.

LLM-optional: offline / no key returns the prefilter order truncated to
``target_n``, so the deterministic path and tests are unaffected. A Sonnet hiccup
falls back to the prefilter order too — selection quality may drop, but a report
is never lost.
"""

from __future__ import annotations

import logging
from datetime import date

from ..config import get_settings

_SUBJECTS = ("omada_self", "competitor", "industry")


def shortlist(
    items: list[dict],
    *,
    report_type: str,
    target_n: int,
    as_of: date | None = None,
) -> list[dict]:
    """Value-select ``items`` down to ~``target_n`` via Sonnet (best-effort)."""
    if target_n <= 0:
        return list(items)
    if len(items) <= target_n or not get_settings().llm_enabled:
        return list(items)[:target_n]

    from . import llm

    try:
        keep = llm.shortlist_items(items, report_type=report_type, target_n=target_n)
    except Exception:  # noqa: BLE001 - a Sonnet hiccup must not drop the report
        logging.getLogger(__name__).warning(
            "shortlist (Sonnet) failed; using prefilter order", exc_info=True
        )
        return list(items)[:target_n]

    picked = _by_indices(items, keep)
    if not picked:
        return list(items)[:target_n]
    picked = _ensure_omada_self(picked, items, target_n)
    return picked[:target_n]


def _by_indices(items: list[dict], indices) -> list[dict]:
    out: list[dict] = []
    seen: set[int] = set()
    for i in indices or []:
        if isinstance(i, int) and 0 <= i < len(items) and i not in seen:
            seen.add(i)
            out.append(items[i])
    return out


def _ensure_omada_self(picked: list[dict], items: list[dict], target_n: int) -> list[dict]:
    """Guarantee the report's namesake subject is represented: if Sonnet dropped
    omada_self entirely but the candidate pool had it, swap the top such candidate
    in (drop the lowest-priority pick to make room)."""
    if any(it.get("subject") == "omada_self" for it in picked):
        return picked
    picked_urls = {it.get("url") for it in picked}
    cand = next(
        (it for it in items if it.get("subject") == "omada_self" and it.get("url") not in picked_urls),
        None,
    )
    if cand is None:
        return picked  # pool genuinely has no omada_self signal this period
    if len(picked) >= target_n:
        picked = picked[:-1]
    picked.append(cand)
    return picked
