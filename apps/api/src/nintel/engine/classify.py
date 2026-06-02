"""Classify stage (Haiku tier).

Per PRD FR-2, the cheap tier assigns three fields to each normalized item:
``summary``, ``category`` and ``signal_strength``. It does **not** make
strategic judgements (that is curate/Opus).

LLM-optional: when ``NINTEL_LLM_ENABLED=true`` this calls Haiku via
:mod:`nintel.engine.llm` with prompt caching; otherwise (default, and in all
tests) it uses the deterministic fixture values that already ride along on the
seed-derived items. The function never mutates strategic fields, so curate
stays the single source of truth for impact/lead/strategy.
"""

from __future__ import annotations

from typing import Any

from ..config import get_settings


# The classifier owns exactly these three contract fields.
CLASSIFIED_FIELDS = ("summary", "category", "signal_strength")


def classify(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate each item with summary/category/signal_strength.

    Returns new dicts (inputs are not mutated).
    """

    settings = get_settings()
    if settings.llm_enabled:
        return _classify_llm(items)
    return [_classify_fixture(item) for item in items]


def _classify_fixture(item: dict[str, Any]) -> dict[str, Any]:
    """Deterministic path: trust the curated fields already on the item.

    The seed-derived items already carry ``summary``/``category``/
    ``signal_strength``. We only fill sensible defaults if a live raw row
    arrived without them, so the stage is safe on non-fixture input too.
    """

    out = dict(item)
    out.setdefault("summary", out.get("title", ""))
    out.setdefault("category", _guess_category(out))
    out.setdefault("signal_strength", "medium")
    return out


def _guess_category(item: dict[str, Any]) -> str:
    source = item.get("source", "")
    if source in {"unifi_release", "unifi_product", "unifi_store"}:
        return "new_product"
    if source == "blog":
        return "firmware"
    if source == "rss":
        return "industry_trend"
    if source == "youtube":
        return "industry"
    return "sentiment"


def _classify_llm(items: list[dict[str, Any]]) -> list[dict[str, Any]]:  # pragma: no cover
    """Haiku path (only when NINTEL_LLM_ENABLED=true)."""

    from . import llm

    out: list[dict[str, Any]] = []
    for item in items:
        result = llm.classify_item(item)
        merged = dict(item)
        for key in CLASSIFIED_FIELDS:
            if key in result:
                merged[key] = result[key]
        out.append(merged)
    return out
