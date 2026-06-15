"""Source G — Gemini deep-research reader.

The "hard to fix-collect" half of the industry signal: upstream supply chain
(networking silicon + memory), competitor strategy, conference/event disclosures,
plus low-frequency protocol breakthroughs and analyst market/share data — none of
which have a stable feed. On each weekly build we run the themes *due* that week
(see ``RESEARCH_THEMES``: weekly themes always; monthly themes on the first build
of the month, with a wider lookback) through Gemini with **Google Search
grounding**, turning the grounded result into real, citable ``subject=industry`` items.

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

from datetime import date, timedelta
from typing import Any

from .base import RawRow, connector_mode_guard, domain_of, seed_rows_for, tier_for_domain

# Research themes with per-theme cadence + lookback. Prompt bodies live in
# prompts/research/<theme>.md so they iterate without code changes.
#
# weekly  -> runs on every weekly build (the dynamic half: supply chain, friend
#            moves, event disclosures).
# monthly -> runs only on the first weekly build of the month, with a wider
#            lookback — low-frequency, high-value signal (protocol breakthroughs as
#            tech foresight; analyst market/share cycles) that would be noise weekly.
RESEARCH_THEMES: dict[str, dict[str, Any]] = {
    "supply_chain": {"cadence": "weekly", "lookback_days": None},
    "competitor": {"cadence": "weekly", "lookback_days": None},
    "conference": {"cadence": "weekly", "lookback_days": None},
    "protocol": {"cadence": "monthly", "lookback_days": 31},
    "market": {"cadence": "monthly", "lookback_days": 31},
}


def _themes_due(run_date: date) -> list[tuple[str, int | None]]:
    """Themes to run on ``run_date``: weekly themes always; monthly themes only on
    the first weekly build of the month (the Monday whose day-of-month is <= 7).
    Returns ``(theme, lookback_days)`` pairs."""

    first_build_of_month = run_date.day <= 7
    return [
        (theme, cfg["lookback_days"])
        for theme, cfg in RESEARCH_THEMES.items()
        if cfg["cadence"] == "weekly" or first_build_of_month
    ]

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
    ``rss`` (the industry web-article channel) but the ``gemini`` glyph surfaces
    the deep-research provenance; the truthful ``source_domain`` + ``url`` +
    ``date`` are what the citation line renders.
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
        "glyph": "gemini",
        "summary": (item.get("summary") or "").strip(),
    }
    return RawRow(source="rss", provenance="G", url=url, title=title, published=published, raw=raw)


class GeminiResearchReader:
    """Reader for the Gemini deep-research industry stream (source G)."""

    name = "gemini:deep_research"
    provenance = "G"
    cadence = "weekly"  # deep-research is a weekly pass — skipped on dailies (cost + semantics)

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

        run_date = date.today()
        run_iso = run_date.isoformat()
        rows: list[RawRow] = []
        for theme, lookback in _themes_due(run_date):
            theme_since = run_date - timedelta(days=lookback) if lookback else since
            items, sources = _research_theme(_theme_prompt(theme, theme_since), settings)
            _archive_memo(theme, items, sources, run_iso, settings)
            for item in items:
                if not (item.get("url") and item.get("title")):
                    continue
                rows.append(map_research_item(item, run_date=run_iso))
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
    import time
    import urllib.error
    import urllib.request

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    data = json.dumps(body).encode("utf-8")
    # The grounded generateContent endpoint returns intermittent 503 ("high demand")
    # and 429s; a single attempt drops the whole G source for the weekly. Retry
    # transient errors with exponential backoff (mirrors the flaky kos relay), but
    # surface hard errors (auth/bad-request) immediately rather than masking them.
    _TRANSIENT = {429, 500, 502, 503, 504}
    attempts = 5
    last_exc: Exception | None = None
    for i in range(attempts):
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310 (trusted host)
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            if exc.code not in _TRANSIENT or i == attempts - 1:
                raise
            last_exc = exc
        except urllib.error.URLError as exc:  # transient network/timeout
            if i == attempts - 1:
                raise
            last_exc = exc
        time.sleep(min(60.0, 4.0 * (2**i)))  # 4s, 8s, 16s, 32s
    raise last_exc  # unreachable, but keeps the type checker honest


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
