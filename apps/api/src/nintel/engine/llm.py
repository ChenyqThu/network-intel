"""Optional Anthropic LLM stage (classify=Haiku, curate=Opus).

This module is **only** imported when ``NINTEL_LLM_ENABLED=true``. The default
pipeline path never touches it, so a fresh checkout and the entire test-suite
run fully offline with no API key and no network. The Anthropic SDK is an
*optional* dependency (``pip install -e .[llm]``).

Design (PRD FR-2.3, the "统一提示词"):

* The shared instructions live in ``prompts/`` (classify.md / curate_daily.md /
  curate_weekly.md) and are sent as the **system** prompt with prompt-caching
  (``cache_control: ephemeral``) so the large, stable instruction block is
  written to cache once and read cheaply on every subsequent item/report. The
  per-item / per-report data goes in the user turn (after the cached prefix),
  which is the correct placement for the prefix-match cache.
* Classify uses Haiku (``claude-haiku-4-5-20251001``); curate uses Opus
  (``claude-opus-4-8``) with adaptive thinking + high effort.
* Both stages request structured JSON via ``output_config.format`` so the
  result is schema-shaped and parseable.

The contract (``report.schema.json``) is the source of truth for both schemas.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from ..config import get_settings

_CLASSIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "category": {
            "type": "string",
            "enum": [
                "bug", "feature_request", "praise", "pain_point", "new_product",
                "pricing", "firmware", "competitor", "sentiment", "industry",
                "industry_trend",
            ],
        },
        "signal_strength": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["summary", "category", "signal_strength"],
}

_BRAND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "i": {"type": "integer"},
                    "brand": {"type": "string", "enum": ["omada", "competitor", "other"]},
                },
                "required": ["i", "brand"],
            },
        },
    },
    "required": ["verdicts"],
}


@lru_cache(maxsize=1)
def _client():  # pragma: no cover - requires network/SDK
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "NINTEL_LLM_ENABLED=true but ANTHROPIC_API_KEY is not set. "
            "Set the key or leave NINTEL_LLM_ENABLED=false to use the fixture path."
        )
    kwargs: dict[str, Any] = {"api_key": settings.anthropic_api_key}
    if settings.anthropic_base_url:  # e.g. a crs / claude-relay-service gateway
        kwargs["base_url"] = settings.anthropic_base_url
    return anthropic.Anthropic(**kwargs)


@lru_cache(maxsize=4)
def _prompt(name: str) -> str:
    path = get_settings().prompts_dir / name
    return path.read_text(encoding="utf-8")


def _cached_system(text: str) -> list[dict[str, Any]]:
    """A single system text block with an ephemeral cache breakpoint.

    The instruction block is stable across all items/reports in a run, so
    caching it means we pay the write once and read it at ~0.1x thereafter.
    """

    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def classify_item(item: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover - network
    """Haiku: return {summary, category, signal_strength} for one raw item."""

    settings = get_settings()
    client = _client()
    # Optional RAG background (default off at classify tier to save cost). Goes
    # in the user turn, never the cached system prefix.
    background = None
    if settings.rag_classify:
        from . import rag

        if rag.kb_enabled():
            hits = rag.retrieve(
                f"{item.get('title', '')} {item.get('summary', '')}",
                collection=rag.COLLECTION_BACKGROUND,
                k=2,
            )
            background = rag.format_context(hits, budget_chars=1600) or None
    # Only the per-item payload varies — keep it out of the cached system prefix.
    user_payload = json.dumps(
        {
            "title": item.get("title"),
            "source": item.get("source"),
            "subject": item.get("subject"),
            "url": item.get("url"),
            "raw_summary": item.get("summary"),
            "metrics": item.get("metrics"),
            "background": background,
        },
        ensure_ascii=False,
    )
    resp = client.messages.create(
        model=settings.haiku_model,
        max_tokens=1024,
        system=_cached_system(_prompt("classify.md")),
        messages=[{"role": "user", "content": user_payload}],
        output_config={"format": {"type": "json_schema", "schema": _CLASSIFY_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    return json.loads(text)


def classify_brands(items: list[dict[str, Any]]) -> dict[int, str]:  # pragma: no cover - network
    """Haiku: disambiguate keyword-tagged candidates by real-world brand.

    Returns ``{index -> "omada"|"competitor"|"other"}`` for the given items (in
    order). Used to filter out things merely *named* Omada (e.g. the Omada E5 EV)
    that keyword matching can't distinguish from TP-Link Omada networking.
    """

    settings = get_settings()
    client = _client()
    payload = json.dumps(
        {
            "items": [
                {
                    "i": i,
                    "title": it.get("title"),
                    "source": it.get("source"),
                    "summary": (it.get("summary") or "")[:200],
                }
                for i, it in enumerate(items)
            ]
        },
        ensure_ascii=False,
    )
    resp = client.messages.create(
        model=settings.haiku_model,
        max_tokens=2048,
        system=_cached_system(_prompt("brand_filter.md")),
        messages=[{"role": "user", "content": payload}],
        output_config={"format": {"type": "json_schema", "schema": _BRAND_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    data = json.loads(text)
    return {int(v["i"]): v["brand"] for v in data.get("verdicts", []) if "i" in v and "brand" in v}


def _loads_report_json(text: str) -> dict[str, Any]:
    """Parse a model's report JSON, tolerating ```json fences / stray prose."""

    s = (text or "").strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
    return json.loads(s)


def admin_edit(doc: dict[str, Any], instruction: str) -> dict[str, Any]:  # pragma: no cover - network
    """Opus: revise a report per a free-text instruction (review-console edit).

    Returns the revised report.json dict (the caller re-finalizes structure/cites
    and validates). The prompt forbids inventing new items/URLs — only existing
    real items may be edited / removed / reordered.
    """

    settings = get_settings()
    client = _client()
    payload = json.dumps({"instruction": instruction, "report": doc}, ensure_ascii=False)
    resp = client.messages.create(
        model=settings.opus_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=_cached_system(_prompt("admin_edit.md")),
        messages=[{"role": "user", "content": payload}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    return _loads_report_json(text)


def curate_report(
    items: list[dict[str, Any]], *, report_type: str, report_id: str
) -> dict[str, Any]:  # pragma: no cover - network
    """Opus: select/order/impact/lead/strategy → a full report.json dict.

    Returns a dict that must pass ``validate_against_schema``. The caller
    (curate.curate) loads + validates it; on any drift the deterministic
    fixture path remains the safe default.
    """

    settings = get_settings()
    client = _client()
    prompt_name = "curate_weekly.md" if report_type == "weekly" else "curate_daily.md"

    # Optional RAG context (background facts + prior coverage for turning-point /
    # "already covered" judgement). User-turn only, so the cached system prefix
    # stays byte-stable.
    context = None
    from . import rag

    if rag.kb_enabled():
        topic = " ".join((it.get("title") or "") for it in items[:12])
        bg = rag.retrieve(topic, collection=rag.COLLECTION_BACKGROUND, k=6)
        prior = []
        for it in items:
            h = rag.retrieve(
                f"{it.get('title', '')} {it.get('summary', '')}",
                collection=rag.COLLECTION_HISTORY,
                k=3,
                filters={"subject": it.get("subject")},
            )
            if h:
                prior.append({"item_id": it.get("id"), "prior": rag.summarize_hits(h)})
        context = {
            "background": rag.format_context(bg, budget_chars=6000),
            "prior_coverage": prior,
        }

    user_payload = json.dumps(
        {
            "report_id": report_id,
            "report_type": report_type,
            "items": items,
            "context": context,
        },
        ensure_ascii=False,
    )
    resp = client.messages.create(
        model=settings.opus_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=_cached_system(_prompt(prompt_name)),
        messages=[{"role": "user", "content": user_payload}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    return json.loads(text)
