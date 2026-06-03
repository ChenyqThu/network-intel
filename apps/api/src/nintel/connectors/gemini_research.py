"""Source G — Gemini deep-research reader.

The "hard to fix-collect" half of the industry signal: protocol milestones, chip
roadmaps/SDK moves, competitor strategy, and conference/forum disclosures that
have no stable feed. Once a week we run a fixed set of themed prompts through
Gemini with **Google Search grounding** and turn the grounded result into real,
citable ``subject=industry`` items.

Two calls per theme — and why (the citation-integrity reason)
-------------------------------------------------------------
The product's #1 rule is real, clickable source URLs (PRD §7.8.6). A single
grounded call with ``responseSchema`` was tried and **fabricates URLs**: the
model grounds the *facts* but, with structured output, ``groundingMetadata``
comes back empty, so it invents plausible-but-404 links. So we split:

1. **ground** — themed prompt + ``google_search``, *no* schema → prose answer +
   ``groundingMetadata.groundingChunks``: the **real** sources Google returned
   (as ``vertexaisearch.../grounding-api-redirect/...`` links). We resolve each
   redirect to its canonical publisher URL.
2. **structure** — feed the grounded prose + the *numbered* real-source list back
   with ``responseSchema`` → items that reference a source by **index**
   (``source_index``). The model never writes a URL; the URL/domain are taken
   from the resolved source list. No invented links can survive.

:func:`map_research_item` maps each item onto :class:`RawRow` (provenance ``G``).
The grounded answer + sources are archived under ``data/research/``. The items
flow through the normal ingest → classify → curate pipeline, so Opus curates from
real grounded sources instead of inventing industry content. Cost lands on the
Gemini key, isolated from the Anthropic budget.

Offline (default / tests) ``fetch`` returns the (currently empty) provenance-``G``
seed rows — no network, no key. Live requires ``NINTEL_CONNECTOR_MODE=live`` +
``G`` ∈ ``NINTEL_LIVE_SOURCES`` + ``NINTEL_GEMINI_API_KEY``.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .base import RawRow, connector_mode_guard, domain_of, seed_rows_for, tier_for_domain

# Fixed weekly research themes (one grounded research pass each). Prompt bodies
# live in prompts/research/<theme>.md so they iterate without code changes.
RESEARCH_THEMES: tuple[str, ...] = ("protocol", "chip", "competitor", "conference")

_LIVE_HINT = (
    "A live reader runs the prompts/research/*.md themes through Gemini with "
    "Google Search grounding (needs NINTEL_GEMINI_API_KEY)."
)

_UA = "Mozilla/5.0 (compatible; NetworkIntelBot/1.0; +https://nintel.chenge.ink)"

# Structuring step output: each item attributes to a real source by INDEX into the
# numbered source list (the model never emits a URL -> no fabricated links).
_RESEARCH_ITEMS_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "source_index": {"type": "integer", "description": "0-based index into the SOURCES list"},
            "date": {"type": "string", "description": "YYYY-MM-DD; empty if unknown"},
            "summary": {"type": "string"},
        },
        "required": ["title", "source_index", "summary"],
    },
}


def _safe_date(value: Any, fallback: str) -> str:
    """ISO date from a loose LLM value, else ``fallback`` (dates can be messy)."""

    s = str(value or "").strip()[:10]
    try:
        date.fromisoformat(s)
    except ValueError:
        return fallback
    return s


def map_research_item(item: dict[str, Any], *, run_date: str) -> RawRow:
    """Map one structured research item -> RawRow (provenance ``G``).

    Pure (no network) — the live path's seam, unit-tested directly. ``source`` is
    ``rss`` (the industry web-article channel; carries a glyph); the truthful
    ``source_domain`` + ``url`` + ``date`` are what the citation line renders.
    """

    url = (item.get("url") or "").strip()
    title = (item.get("title") or "").strip()
    domain = (item.get("source_domain") or "").strip() or domain_of(url)
    published = _safe_date(item.get("date"), run_date)
    raw: dict[str, Any] = {
        "source": "rss",
        "provenance": "G",
        "url": url,
        "title": title,
        "date": published,
        "source_domain": domain,
        "source_tier": tier_for_domain(domain),
        "subject": "industry",
        "category": "industry_trend",
        "glyph": "rss",
        "summary": (item.get("summary") or "").strip(),
    }
    return RawRow(source="rss", provenance="G", url=url, title=title, published=published, raw=raw)


class GeminiResearchReader:
    """Reader for the Gemini deep-research industry stream (source G)."""

    name = "gemini:deep_research"
    provenance = "G"

    def fetch(self, since: date) -> list[RawRow]:
        if connector_mode_guard(self.name, _LIVE_HINT, self.provenance):
            return [r for r in self._research_live(since) if r.date >= since]
        # No provenance-G seed yet -> empty offline (valid: no research items).
        rows = seed_rows_for(provenances={"G"})
        return [r for r in rows if r.date >= since]

    def _research_live(self, since: date) -> list[RawRow]:  # pragma: no cover - network
        from ..config import get_settings

        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError(
                "source G is live but NINTEL_GEMINI_API_KEY is not set. Set the key, "
                "or drop G from NINTEL_LIVE_SOURCES."
            )

        run_date = date.today().isoformat()
        rows: list[RawRow] = []
        for theme in RESEARCH_THEMES:
            items, sources = _research_theme(_theme_prompt(theme, since), settings)
            _archive_memo(theme, items, sources, run_date, settings)
            for item in items:
                if not (item.get("url") and item.get("title")):
                    continue
                rows.append(map_research_item(item, run_date=run_date))
        return rows


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------
def _prompt(rel: str) -> str:
    from ..config import get_settings

    return (get_settings().prompts_dir / "research" / rel).read_text(encoding="utf-8")


def _theme_prompt(theme: str, since: date) -> str:
    """The grounding-pass prompt: themed research instruction + time window."""

    return (
        f"{_prompt(f'{theme}.md')}\n\n"
        f"时间范围：聚焦 {since.isoformat()} 至今的最新动态，越新越好。"
    )


# ---------------------------------------------------------------------------
# Gemini calls (urllib, no SDK — mirrors the Supabase reader's _pg_get)
# ---------------------------------------------------------------------------
def _gemini_call(body: dict[str, Any], settings) -> dict[str, Any]:  # pragma: no cover - network
    import json
    import urllib.request

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read().decode("utf-8", "replace"))


def _parts_text(cand: dict[str, Any]) -> str:  # pragma: no cover - network
    parts = (cand.get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts)


def _ground(prompt: str, settings) -> tuple[str, list[dict[str, str]]]:  # pragma: no cover - network
    """Call 1: grounded prose + real source chunks ({uri,title}), no schema."""

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
    }
    resp = _gemini_call(body, settings)
    cand = (resp.get("candidates") or [{}])[0]
    chunks: list[dict[str, str]] = []
    for ch in (cand.get("groundingMetadata") or {}).get("groundingChunks") or []:
        web = ch.get("web") or {}
        if web.get("uri"):
            chunks.append({"uri": web["uri"], "title": web.get("title", "")})
    return _parts_text(cand), chunks


def _resolve_redirect(uri: str) -> str:  # pragma: no cover - network
    """Resolve a grounding-api-redirect link to its canonical publisher URL.

    Best-effort: returns the redirect URL unchanged if resolution fails (it still
    navigates to the source when clicked).
    """

    import urllib.request

    try:
        req = urllib.request.Request(uri, headers={"User-Agent": _UA}, method="GET")
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            return r.geturl() or uri
    except Exception:  # noqa: BLE001 - resolution is best-effort
        return uri


def _resolve_sources(chunks: list[dict[str, str]]) -> list[dict[str, str]]:  # pragma: no cover - network
    """Grounding chunks -> [{url, domain}] with canonical URLs (deduped)."""

    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for ch in chunks:
        url = _resolve_redirect(ch["uri"])
        if url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "domain": domain_of(url) or ch.get("title", "")})
    return out


def _structure(text: str, sources: list[dict[str, str]], settings) -> list[dict[str, Any]]:  # pragma: no cover - network
    """Call 2: grounded prose + numbered real sources -> items w/ source_index.

    Attaches the real url/domain from ``sources[source_index]`` so no model-written
    (and possibly hallucinated) URL can enter the pool.
    """

    import json

    listing = "\n".join(f"[{i}] {s['domain']}" for i, s in enumerate(sources))
    prompt = f"{_prompt('structure.md')}\n\n## 研究记录\n{text}\n\n## 来源列表（SOURCES）\n{listing}"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _RESEARCH_ITEMS_SCHEMA,
        },
    }
    resp = _gemini_call(body, settings)
    cand = (resp.get("candidates") or [{}])[0]
    try:
        raw_items = json.loads(_parts_text(cand) or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(raw_items, list):
        return []

    items: list[dict[str, Any]] = []
    for it in raw_items:
        idx = it.get("source_index")
        if not isinstance(idx, int) or not (0 <= idx < len(sources)):
            continue  # drop items we can't attribute to a real source
        src = sources[idx]
        items.append({
            "title": it.get("title", ""),
            "url": src["url"],
            "source_domain": src["domain"],
            "date": it.get("date", ""),
            "summary": it.get("summary", ""),
        })
    return items


def _research_theme(theme_prompt: str, settings) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:  # pragma: no cover - network
    """One theme: ground -> resolve real sources -> structure by index."""

    text, chunks = _ground(theme_prompt, settings)
    sources = _resolve_sources(chunks)
    if not sources:
        return [], []
    return _structure(text, sources, settings), sources


def _archive_memo(
    theme: str, items: list[dict[str, Any]], sources: list[dict[str, str]], run_date: str, settings
) -> None:  # pragma: no cover - filesystem
    """Persist the structured items + their real sources as the audit record."""

    y, w, _ = date.fromisoformat(run_date).isocalendar()
    out_dir = settings.research_dir / f"{y}-W{w:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {theme} · {run_date}", "", f"{len(items)} items", ""]
    for it in items:
        lines.append(f"- **{it.get('title', '')}** ({it.get('date', '') or 'n/a'}) — {it.get('summary', '')}")
        lines.append(f"  {it.get('url', '')}")
    lines += ["", "## Sources"]
    lines += [f"- {s['domain']} — {s['url']}" for s in sources]
    (out_dir / f"{theme}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
