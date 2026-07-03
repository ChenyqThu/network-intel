"""Optional Anthropic LLM stage (classify=Haiku, curate=Sonnet 5).

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
* Classify uses Haiku (``claude-haiku-4-5-20251001``); curate uses Sonnet 5
  (``claude-sonnet-5``) with adaptive thinking + high effort.
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
        # key_claim: one-line atomic verifiable fact/data point (or "" if none).
        # An internal signal for curate (sharper leads + a stable cross-day dedup
        # key); pruned from the closed report contract, kept on the stored item.
        "key_claim": {"type": "string"},
        # community_view / top_insight: extracted from community_context (the Notion
        # page body — comments/discussion) when present; "" otherwise. Internal
        # signals for curate, pruned from the closed report contract.
        "community_view": {"type": "string"},
        "top_insight": {"type": "string"},
    },
    "required": [
        "summary", "category", "signal_strength", "key_claim",
        "community_view", "top_insight",
    ],
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

_SHORTLIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"selected": {"type": "array", "items": {"type": "integer"}}},
    "required": ["selected"],
}

_PAINS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    # member item indices (into the input) belonging to this theme.
                    "members": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["name", "members"],
            },
        },
    },
    "required": ["themes"],
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
            # Notion page body (selftext + community comments + any transcript)
            # for shortlisted Source-A items — the substance behind the title.
            "community_context": item.get("community_context"),
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
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return _loads_json(text)


def shortlist_items(
    items: list[dict[str, Any]], *, report_type: str, target_n: int
) -> list[int]:  # pragma: no cover - network
    """Sonnet 精选: value-select the most decision-relevant candidates.

    Returns kept candidate **indices** into ``items`` (highest value first). The
    model only selects — it never generates content, so NO-FABRICATION holds.
    """
    settings = get_settings()
    client = _client()
    from .trend import heat_score

    candidates = [
        {
            "i": i,
            "subject": it.get("subject"),
            "source": it.get("source"),
            "provenance": it.get("provenance"),
            "title": it.get("title"),
            "summary": (it.get("summary") or "")[:240],
            "date": it.get("date"),
            "heat": int(heat_score(it)),
            "sentiment": it.get("sentiment"),
            "switch_intent": it.get("switch_intent"),
            "category": it.get("category"),
        }
        for i, it in enumerate(items)
    ]
    user_payload = json.dumps(
        {"report_type": report_type, "target_n": target_n, "candidates": candidates},
        ensure_ascii=False,
    )
    resp = client.messages.create(
        model=settings.sonnet_model,
        max_tokens=2048,
        # Sonnet 5 does extended thinking by default, which would consume the whole
        # token budget before emitting the selection JSON (→ empty → silent prefilter
        # fallback). 精选 is index-selection, not reasoning, so disable thinking.
        thinking={"type": "disabled"},
        system=_cached_system(_prompt("shortlist.md")),
        messages=[{"role": "user", "content": user_payload}],
        output_config={"format": {"type": "json_schema", "schema": _SHORTLIST_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    data = json.loads(text)
    sel = data.get("selected") if isinstance(data, dict) else None
    return [i for i in sel if isinstance(i, int)] if isinstance(sel, list) else []


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


def cluster_pains(items: list[dict[str, Any]]) -> list[dict[str, Any]]:  # pragma: no cover - network
    """Sonnet: cluster real UniFi-community complaints into named pain themes.

    Returns ``[{name, members:[int]}]`` where ``members`` are indices into
    ``items``. The model only names + groups real items (never invents entries or
    counts — the engine counts real members), so NO-FABRICATION holds.
    """

    settings = get_settings()
    client = _client()
    payload = json.dumps(
        {
            "items": [
                {
                    "i": i,
                    "title": it.get("title"),
                    "summary": (it.get("summary") or "")[:200],
                    "sentiment": it.get("sentiment"),
                }
                for i, it in enumerate(items)
            ]
        },
        ensure_ascii=False,
    )
    resp = client.messages.create(
        model=settings.sonnet_model,
        max_tokens=2048,
        # Sonnet 5 does extended thinking by default, which would consume the whole
        # token budget before emitting the themes JSON (→ empty pains, no error).
        # Clustering is structured extraction, not reasoning, so disable thinking.
        thinking={"type": "disabled"},
        system=_cached_system(_prompt("pains.md")),
        messages=[{"role": "user", "content": payload}],
        output_config={"format": {"type": "json_schema", "schema": _PAINS_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    data = json.loads(text)
    themes = data.get("themes") if isinstance(data, dict) else None
    out: list[dict[str, Any]] = []
    if isinstance(themes, list):
        for t in themes:
            if not isinstance(t, dict) or not isinstance(t.get("name"), str):
                continue
            members = [m for m in (t.get("members") or []) if isinstance(m, int)]
            out.append({"name": t["name"].strip(), "members": members})
    return out


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
        timeout=900.0,  # weekly docs are large; default SDK timeout is too tight
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    return _loads_report_json(text)


def _loads_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from the model's text, tolerating ```json fences / prose.

    Tiers that force ``json_schema`` output return clean JSON, but the curate
    tier runs free-form (thinking + high effort) and occasionally wraps the
    object in a markdown fence or a leading sentence. Try the raw text first,
    otherwise extract the outermost ``{...}`` object. On genuinely empty/garbage
    output raise a clear error (with a head sample) so failures are diagnosable
    instead of a naked, context-free JSONDecodeError.
    """

    s = (text or "").strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(s[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(
        f"LLM returned no parseable JSON (len={len(s)}, head={s[:120]!r})"
    )


def curate_report(
    items: list[dict[str, Any]],
    *,
    report_type: str,
    report_id: str,
    recent_coverage: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:  # pragma: no cover - network
    """Sonnet 5: select/order/impact/lead/strategy → a full report.json dict.

    Returns a dict that must pass ``validate_against_schema``. The caller
    (curate.curate) loads + validates it; on any drift the deterministic
    fixture path remains the safe default.
    """

    settings = get_settings()
    client = _client()
    prompt_name = "curate_weekly.md" if report_type == "weekly" else "curate_daily.md"

    # Context for the curator (user-turn only, so the cached system prefix stays
    # byte-stable): optional RAG background + vector prior_coverage, plus the
    # recent-coverage digest (B1) — the latter is independent of RAG (no
    # embedder), the reliable temporal-dedup signal. All reference-only.
    context: dict[str, Any] = {}
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
        context["background"] = rag.format_context(bg, budget_chars=6000)
        context["prior_coverage"] = prior

    if recent_coverage:
        context["recent_coverage"] = recent_coverage

    user_payload = json.dumps(
        {
            "report_id": report_id,
            "report_type": report_type,
            "items": items,
            "context": context or None,
        },
        ensure_ascii=False,
    )
    # max_tokens covers adaptive *thinking* + the full report JSON. A weekly
    # (strategy + dashboard + 4-8 insights + items, all Chinese) was truncating at
    # 16k — an incomplete JSON body _loads_json can't parse, which crashes the
    # build with no fallback. Pin to the model's max (64k for claude-sonnet-5,
    # probe-verified accepted) so output room is never the failure mode again; a
    # real report only uses ~10-15k, so this is purely a ceiling.
    # An explicit per-request timeout is REQUIRED at this size: the SDK otherwise
    # raises "Streaming is required for operations that may take longer than 10
    # minutes" (it estimates 3600*max_tokens/128000 s and refuses a non-streaming
    # call past 600s). Passing timeout bypasses that guard and keeps the same
    # non-streaming path that works at smaller sizes.
    resp = client.messages.create(
        model=settings.sonnet_model,
        max_tokens=64000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=_cached_system(_prompt(prompt_name)),
        messages=[{"role": "user", "content": user_payload}],
        timeout=900.0,
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return _loads_json(text)
