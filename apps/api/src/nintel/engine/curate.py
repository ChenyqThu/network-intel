"""Curate stage (Sonnet 5 tier).

This is the strategic stage (PRD FR-2.3): from the pool of classified items it

* selects + orders items into the cadence-appropriate sections,
* assigns the **subject-aware** ``omada_impact``
  (omada_self → needs_fix|feature_input|strength_confirm;
   competitor → threat|opportunity|neutral; industry → opportunity|neutral),
* writes the ``impact_note`` research line,
* synthesizes the ``lead`` and (weekly only) the ``strategy`` block with
  ``{{cite:N}}`` superscripts,
* assigns ``cite_id`` and builds the numbered ``references`` list,
* fills ``tally`` and ``store`` (weekly).

It then hands ``stats``/``dashboard`` to :mod:`nintel.engine.trend`.

LLM-optional: ``NINTEL_LLM_ENABLED=true`` routes the synthesis through Sonnet 5 via
:mod:`nintel.engine.llm` (with prompt caching). The default deterministic path
reproduces the human-verified seed report **exactly**, driven by the curated
seed as the curation manifest — so output is offline and lossless.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..contract import Report, load_report

# Subject -> the impact vocabulary that subject is allowed to take (PRD §2.1).
IMPACT_VOCAB: dict[str, set[str]] = {
    "omada_self": {"needs_fix", "feature_input", "strength_confirm"},
    "competitor": {"threat", "opportunity", "neutral"},
    "industry": {"opportunity", "neutral", "threat"},
}

REPORT_IDS = {"daily": "2026-06-01-daily", "weekly": "2026-W22-weekly"}

_CITE_RE = re.compile(r"\{\{cite:(\d+)\}\}")


def _cites_in(text: str) -> set[int]:
    """All ``{{cite:N}}`` numbers in ``text``."""
    return {int(m) for m in _CITE_RE.findall(text or "")}


# Selection reason -> re-surface badge (reuses the optional, already-rendered
# IntelItem.badges field; no contract/schema change).
_REASON_BADGE = {
    "resurface:heat": "热度激增",
    "resurface:sentiment": "情绪反转",
    "resurface:switch": "切换意图↑",
}


@lru_cache(maxsize=4)
def _seed(report_id: str) -> dict[str, Any]:
    path: Path = get_settings().contract_dir / f"{report_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_subject_impact(item: dict[str, Any]) -> None:
    """Assert an item's ``omada_impact`` is legal for its ``subject``.

    Raises ``ValueError`` on a subject/impact mismatch (the invariant curate is
    responsible for upholding). ``unknown`` is always permitted as a fallback.
    """

    subject = item["subject"]
    impact = item["omada_impact"]
    allowed = IMPACT_VOCAB.get(subject, set()) | {"unknown"}
    if impact not in allowed:
        raise ValueError(
            f"item {item.get('id')!r}: impact {impact!r} is not valid for "
            f"subject {subject!r} (allowed: {sorted(allowed)})"
        )


def curate(
    items: list[dict[str, Any]],
    *,
    report_type: str,
    report_id: str | None = None,
    generated_at: str | None = None,
    report_date: str | None = None,
    reasons: dict[str, str] | None = None,
    recent_coverage: list[dict[str, Any]] | None = None,
) -> Report:
    """Assemble a validated :class:`Report` from classified items.

    The default path uses the seed report as the curation manifest: it pins the
    section membership/order, impact assignments, lead/strategy synthesis and
    reference numbering that the team has verified, and rebuilds the report from
    the live item pool so cite_id↔reference integrity is enforced in code (not
    just copied). The result is content-equivalent to the seed.
    """

    if report_type not in REPORT_IDS:
        raise ValueError(f"unknown report_type: {report_type!r}")

    rid = report_id or REPORT_IDS[report_type]
    settings = get_settings()
    if settings.llm_enabled:  # pragma: no cover - network path
        from . import llm

        doc = llm.curate_report(
            items, report_type=report_type, report_id=rid, recent_coverage=recent_coverage
        )
        # LLM output can carry stray keys; the contract is closed
        # (additionalProperties:false). Prune to allowed keys, then fill the
        # structural fields we own + guarantee the cite bijection.
        doc = _clean_to_schema(doc)
        # Reconcile against the real input pool: drop any item the LLM invented
        # (url not in the pool), and backfill required fields from the real
        # classified item — overlaying only the LLM's judgments. Guarantees every
        # emitted item is real + schema-complete.
        doc = _reconcile_items(doc, items)
        doc = _normalize_llm_doc(
            doc, report_type=report_type, report_id=rid,
            generated_at=generated_at, report_date=report_date,
        )
        # The section taxonomy is fixed per cadence — the engine assembles it
        # from each item's subject (and groups synthesized insights), not the LLM
        # (which drifts).
        insights = doc.get("insights") or []
        doc["sections"] = _assemble_sections(doc.get("items", []), report_type, insights)
        doc = assign_cite_ids(doc)
        # The LLM lead/strategy/insights may cite numbers that don't map to any
        # item; drop those dangling placeholders rather than fail the report.
        _strip_unresolved_cites(doc)
        # Synthesized mode: references == cited sources only.
        if insights:
            _prune_to_cited(doc, report_type)
        if reasons:
            _apply_resurface_badges(doc, reasons)
        _assert_citation_integrity(doc)
        return load_report(doc)

    return _curate_fixture(items, report_type=report_type, report_id=rid, generated_at=generated_at)


def _curate_fixture(
    items: list[dict[str, Any]],
    *,
    report_type: str,
    report_id: str,
    generated_at: str | None,
) -> Report:
    seed = _seed(report_id)

    # Index the live item pool by URL — the stable join key between the raw
    # ingest stream and the curation manifest.
    pool: dict[str, dict[str, Any]] = {it["url"]: it for it in items}

    # Build the curated item list in the manifest's order, pulling content from
    # the live pool where available and falling back to the manifest item.
    curated_items: list[dict[str, Any]] = []
    for manifest_item in seed["items"]:
        live = pool.get(manifest_item["url"])
        merged = dict(live) if live else {}
        # The manifest owns the strategic/identity fields; classify owns summary
        # & category & signal_strength (already on the live item, but the
        # manifest is authoritative for the curated wording).
        merged.update(manifest_item)
        validate_subject_impact(merged)
        # Prune internal-only fields the live item carries (key_claim /
        # community_view / top_insight / community_context / notion_page_id …) —
        # the report contract is closed (additionalProperties:false). Mirrors the
        # LLM path's _reconcile_items prune so the offline path stays schema-valid.
        curated_items.append(_prune(merged, _ALLOWED_ITEM))

    # References: derive from the manifest, then assert cite_id integrity below.
    references = [dict(ref) for ref in seed["references"]]

    doc: dict[str, Any] = {
        "report_id": report_id,
        "type": report_type,
        "date": seed["date"],
        "date_range": seed["date_range"],
        "generated_at": generated_at or seed["generated_at"],
        "title": seed.get("title"),
        "lead": seed["lead"],
        "strategy": seed.get("strategy"),
        "tally": seed.get("tally"),
        "sections": seed["sections"],
        "items": curated_items,
        "references": references,
        "store": seed.get("store", []),
        # stats + dashboard are produced by the trend stage (see pipeline);
        # seed them here so curate alone yields a valid report.
        "stats": seed["stats"],
        "dashboard": seed.get("dashboard"),
    }

    _assert_citation_integrity(doc)
    return load_report(doc)


# Allowed keys per contract level (report.schema.json, additionalProperties:false).
_ALLOWED_TOP = {
    "report_id", "type", "date", "date_range", "generated_at", "title", "lead",
    "strategy", "tally", "sections", "items", "insights", "references", "store",
    "stats", "funnel", "dashboard",
}
_ALLOWED_ITEM = {
    "id", "cite_id", "subject", "source", "source_domain", "source_tier", "source_label",
    "tier_label", "glyph", "provenance", "title", "stage", "badges", "summary", "category",
    "signal_strength", "omada_impact", "impact_note", "metrics", "sentiment", "relevance",
    "switch_intent", "date", "url",
}
_ALLOWED_REF = {"cite_id", "title", "source_domain", "source_tier", "tier_label", "date", "url"}
_ALLOWED_SECTION = {"key", "title", "icon", "desc", "items", "insights"}
_ALLOWED_INSIGHT = {"id", "subject", "title", "body", "takeaway", "omada_impact", "cite_refs"}
_ALLOWED_LEAD = {"text", "strong", "cite_refs"}
_ALLOWED_STRATEGY = {"title", "period", "paras", "body", "cite_refs"}
_ALLOWED_STORE = {"product", "cat", "from", "to", "change", "dir", "stock"}
_ALLOWED_TALLY = {"signals", "threat", "opp", "neutral", "official"}


_SECTION_TITLES = {
    "omada_self": "Omada 自身舆情",
    "competitor": "竞品动态",
    "sentiment": "竞品舆情与对比",
    "industry": "行业要闻",
    "store": "Store 动向",
    "dashboard": "数据看板",
}
_SECTIONS_BY_TYPE = {
    "daily": ["omada_self", "competitor", "sentiment", "industry"],
    "weekly": ["omada_self", "competitor", "sentiment", "store", "industry", "dashboard"],
}
# Synthesized mode collapses the competitor/sentiment split into one competitor
# section (insights synthesize across official + community sources), keyed purely
# by subject.
# Daily focuses on 舆情 (Omada self + competitor); industry/RSS is weekly-only.
_SECTIONS_BY_TYPE_SYNTH = {
    "daily": ["omada_self", "competitor"],
    "weekly": ["omada_self", "competitor", "store", "industry", "dashboard"],
}
_OFFICIAL_SOURCES = {"unifi_release", "blog", "unifi_product", "unifi_store"}


def _subject_section(subject: str | None) -> str:
    """Map a subject to its synthesized-mode section key."""
    if subject == "omada_self":
        return "omada_self"
    if subject == "industry":
        return "industry"
    return "competitor"


def _section_for_item(it: dict[str, Any]) -> str:
    subject = it.get("subject")
    if subject == "omada_self":
        return "omada_self"
    if subject == "industry":
        return "industry"
    # competitor (or unknown): official moves vs community sentiment
    return "competitor" if it.get("source") in _OFFICIAL_SOURCES else "sentiment"


def _assemble_sections(
    items: list[dict[str, Any]],
    report_type: str,
    insights: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Deterministically build the cadence's fixed sections.

    Synthesized mode (``insights`` present): subject-keyed sections, each carrying
    its insight ids (what the frontend renders) plus its item ids (for reference
    grouping / cite ordering). Legacy mode: per-item sections (competitor/sentiment
    split). store / dashboard stay item-less (frontend renders report.store /
    report.dashboard); they appear so the contract order holds.
    """
    if insights:
        keys = _SECTIONS_BY_TYPE_SYNTH.get(report_type, _SECTIONS_BY_TYPE_SYNTH["daily"])
        item_buckets: dict[str, list[str]] = {k: [] for k in keys}
        for it in items:
            sec = _subject_section(it.get("subject"))
            if sec in item_buckets:
                item_buckets[sec].append(it["id"])
        ins_buckets: dict[str, list[str]] = {k: [] for k in keys}
        for ins in insights:
            sec = _subject_section(ins.get("subject"))
            if sec in ins_buckets:
                ins_buckets[sec].append(ins["id"])
        out: list[dict[str, Any]] = []
        for k in keys:
            sec_obj: dict[str, Any] = {
                "key": k, "title": _SECTION_TITLES[k], "items": item_buckets.get(k, []),
            }
            if ins_buckets.get(k):
                sec_obj["insights"] = ins_buckets[k]
            out.append(sec_obj)
        return out

    keys = _SECTIONS_BY_TYPE.get(report_type, _SECTIONS_BY_TYPE["daily"])
    buckets: dict[str, list[str]] = {k: [] for k in keys}
    for it in items:
        sec = _section_for_item(it)
        if sec not in buckets:
            sec = "industry" if "industry" in buckets else keys[0]
        buckets[sec].append(it["id"])
    return [{"key": k, "title": _SECTION_TITLES[k], "items": buckets.get(k, [])} for k in keys]


def _prune(d: Any, allowed: set[str]) -> Any:
    return {k: v for k, v in d.items() if k in allowed} if isinstance(d, dict) else d


def _clean_to_schema(doc: dict[str, Any]) -> dict[str, Any]:
    """Drop keys the closed contract doesn't allow (LLM output can drift).

    metrics/stats/dashboard are open objects, so their contents are left intact.
    """
    doc = _prune(doc, _ALLOWED_TOP)
    if isinstance(doc.get("lead"), dict):
        doc["lead"] = _prune(doc["lead"], _ALLOWED_LEAD)
    if isinstance(doc.get("strategy"), dict):
        doc["strategy"] = _prune(doc["strategy"], _ALLOWED_STRATEGY)
    if isinstance(doc.get("tally"), dict):
        doc["tally"] = _prune(doc["tally"], _ALLOWED_TALLY)
    if isinstance(doc.get("items"), list):
        doc["items"] = [_prune(it, _ALLOWED_ITEM) for it in doc["items"] if isinstance(it, dict)]
    if isinstance(doc.get("insights"), list):
        doc["insights"] = [_prune(ins, _ALLOWED_INSIGHT) for ins in doc["insights"] if isinstance(ins, dict)]
    if isinstance(doc.get("references"), list):
        doc["references"] = [_prune(r, _ALLOWED_REF) for r in doc["references"] if isinstance(r, dict)]
    if isinstance(doc.get("sections"), list):
        doc["sections"] = [_prune(s, _ALLOWED_SECTION) for s in doc["sections"] if isinstance(s, dict)]
    if isinstance(doc.get("store"), list):
        # StoreRow requires a real product name + stock. Drop rows the LLM emits
        # without them rather than crashing the build on contract validation, and
        # never fabricate the missing fields. Real store moves are attached
        # separately from Supabase (pipeline._attach_store_moves).
        rows = (_prune(r, _ALLOWED_STORE) for r in doc["store"] if isinstance(r, dict))
        doc["store"] = [r for r in rows if r.get("product") and r.get("stock")]
    return doc


_SUBJECT_BY_SOURCE = {
    "rss": "industry",
    "omada_community": "omada_self",
    "reddit": "competitor", "youtube": "competitor",
    "unifi_release": "competitor", "unifi_community": "competitor", "blog": "competitor",
    "unifi_store": "competitor", "unifi_product": "competitor",
}
# When the LLM omits a per-item impact (e.g. the weekly path emits sections but
# no items[] judgments), fall back to a *valid, sensible* impact for the subject
# rather than the uninformative "unknown" (which leaves the tally empty).
_DEFAULT_IMPACT_BY_SUBJECT = {"competitor": "neutral", "industry": "neutral"}
# Per-item fields the LLM is allowed to set/override; everything else comes from
# the real classified item.
_JUDGMENT_KEYS = (
    "subject", "omada_impact", "impact_note", "signal_strength", "badges",
    "stage", "summary", "category",
)
# Enum whitelists — the LLM sometimes drifts (e.g. puts an impact value like
# "feature_input" into `category`). Reject drifted enum values and keep the real
# classified value instead, so a closed-enum schema field never fails validation.
_VALID_SUBJECT = {"omada_self", "competitor", "industry"}
_VALID_CATEGORY = {
    "bug", "feature_request", "praise", "pain_point", "new_product", "pricing",
    "firmware", "competitor", "sentiment", "industry", "industry_trend",
}
_VALID_IMPACT = {
    "threat", "opportunity", "neutral", "needs_fix", "feature_input",
    "strength_confirm", "unknown",
}
_VALID_STRENGTH = {"high", "medium", "low"}
_ENUM_GUARDS = {
    "subject": _VALID_SUBJECT, "category": _VALID_CATEGORY,
    "omada_impact": _VALID_IMPACT, "signal_strength": _VALID_STRENGTH,
}


def _reconcile_items(doc: dict[str, Any], input_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Rebuild items from the real input pool + the LLM's judgments.

    Keeps only items whose ``url`` is in the pool (drops anything the LLM
    invented), copies the real classified fields (summary/category/source/url/…),
    overlays the LLM's judgment fields, and fills a source-derived subject /
    ``unknown`` impact if the LLM omitted them. Result: every item is real and
    schema-complete.
    """
    # The item LIST is the real selected pool (the engine decided it via select);
    # the LLM only supplies per-item JUDGMENTS, matched by url. This way the
    # report is never empty even if the LLM omits/garbles its items array.
    llm_by_url = {li.get("url"): li for li in doc.get("items", []) if isinstance(li, dict) and li.get("url")}
    out: list[dict[str, Any]] = []
    for idx, base in enumerate(input_items):
        merged = dict(base)
        li = llm_by_url.get(base.get("url"), {})
        for k in _JUDGMENT_KEYS:
            v = li.get(k)
            if v in (None, ""):
                continue
            guard = _ENUM_GUARDS.get(k)
            if guard and v not in guard:
                continue  # LLM drifted on this enum -> keep the real classified value
            merged[k] = v
        merged["id"] = li.get("id") or merged.get("id") or f"i{idx + 1}"
        # Preserve the LLM's *provisional* cite_id so assign_cite_ids can remap
        # insight/lead/strategy citations (provisional -> final). Items the LLM
        # didn't number get a final cite_id but no provisional mapping.
        if isinstance(li.get("cite_id"), int):
            merged["cite_id"] = li["cite_id"]
        if merged.get("subject") not in _VALID_SUBJECT:
            merged["subject"] = _SUBJECT_BY_SOURCE.get(merged.get("source"), "competitor")
        # impact must be valid for the subject (PRD §2.1); else a sensible default.
        allowed = IMPACT_VOCAB.get(merged["subject"], set()) | {"unknown"}
        if merged.get("omada_impact") not in allowed:
            merged["omada_impact"] = _DEFAULT_IMPACT_BY_SUBJECT.get(merged["subject"], "unknown")
        if merged.get("category") not in _VALID_CATEGORY:
            merged["category"] = "industry" if merged["subject"] == "industry" else "sentiment"
        # Drop internal-only fields carried on the classified item (key_claim,
        # community_view/top_insight, community_context, notion_page_id, …): they
        # fed the LLM but the report contract is closed (additionalProperties:false).
        out.append(_prune(merged, _ALLOWED_ITEM))
    doc["items"] = out
    return doc


def _normalize_llm_doc(
    doc: dict[str, Any], *, report_type: str, report_id: str,
    generated_at: str | None, report_date: str | None = None,
) -> dict[str, Any]:
    """Fill the structural/identity fields the engine owns, so a valid report
    never depends on the LLM remembering to emit them. The LLM produces the
    editorial content (lead / sections / items / references / strategy); we set
    report_id, type, dates, and a stats placeholder (trend recomputes stats)."""

    doc["report_id"] = report_id
    doc["type"] = report_type
    doc["generated_at"] = doc.get("generated_at") or generated_at or default_generated_at()
    doc["date"] = report_date or doc.get("date") or date.today().isoformat()
    doc.setdefault("date_range", doc["date"])
    doc.setdefault("items", [])
    doc.setdefault("insights", [])
    _sanitize_insights(doc)
    if not isinstance(doc.get("lead"), dict):
        doc["lead"] = {"text": "", "cite_refs": []}
    # stats + dashboard are recomputed by the trend stage — force clean values
    # so a malformed LLM block (e.g. top_hot of strings) can't fail validation.
    doc["stats"] = {"total_items": len(doc.get("items", []))}
    doc.setdefault("references", [])
    # store must be an array of rows; the LLM sometimes emits a table object.
    if not isinstance(doc.get("store"), list):
        doc["store"] = []
    if report_type == "daily":
        doc["strategy"] = None  # daily must not carry a strategy block
        doc["dashboard"] = None
    if not doc.get("title"):
        if report_type == "weekly":
            period = report_id.replace("-weekly", "")  # e.g. 2026-W22
            doc["title"] = f"Omada 洞察情报周报 · {period}"
        else:
            doc["title"] = f"Omada 洞察情报日报 · {doc['date']}"
    _ensure_lead(doc)
    return doc


def _sanitize_insights(doc: dict[str, Any]) -> None:
    """Drop malformed insights and coerce drifted enums so the closed schema
    never fails on an LLM-authored insight (id/subject/title/body/cite_refs are
    required; subject/omada_impact are closed enums)."""
    out: list[dict[str, Any]] = []
    for i, ins in enumerate(doc.get("insights") or []):
        if not isinstance(ins, dict):
            continue
        title = (ins.get("title") or "").strip()
        body = (ins.get("body") or "").strip()
        if not title or not body:
            continue  # required fields missing -> not a usable insight
        ins["id"] = ins.get("id") or f"ins{i + 1}"
        ins["title"] = title
        ins["body"] = body
        if ins.get("subject") not in _VALID_SUBJECT:
            ins["subject"] = "competitor"
        cr = ins.get("cite_refs")
        ins["cite_refs"] = [n for n in cr if isinstance(n, int)] if isinstance(cr, list) else []
        if ins.get("omada_impact") not in _VALID_IMPACT:
            ins.pop("omada_impact", None)
        if "takeaway" in ins and not isinstance(ins["takeaway"], str):
            ins.pop("takeaway", None)
        out.append(ins)
    doc["insights"] = out


def _ensure_lead(doc: dict[str, Any]) -> None:
    """Guarantee a non-empty ``lead`` (导语).

    The weekly LLM sometimes pours its summary into ``strategy`` and leaves the
    lead empty (the bug that shipped a blank 周报导语). The prompt now requires a
    lead; this is the safety net: synthesize a one-liner from the top insight
    titles (cites stripped so the fallback never dangles), else from strategy.
    """
    lead = doc.get("lead")
    if not isinstance(lead, dict):
        lead = {"text": "", "cite_refs": []}
        doc["lead"] = lead
    lead.setdefault("cite_refs", [])
    if (lead.get("text") or "").strip():
        return
    insights = [i for i in (doc.get("insights") or []) if isinstance(i, dict)]
    titles = [_CITE_RE.sub("", (i.get("title") or "")).strip() for i in insights[:3]]
    titles = [t for t in titles if t]
    if titles:
        lead["text"] = "本期看点：" + "；".join(titles) + "。"
        return
    strat = doc.get("strategy")
    if isinstance(strat, dict):
        body = strat.get("body") or ""
        if not body and isinstance(strat.get("paras"), list) and strat["paras"]:
            p0 = strat["paras"][0]
            body = p0[1] if len(p0) > 1 else ""
        lead["text"] = _CITE_RE.sub("", body).strip()


def assign_cite_ids(doc: dict[str, Any]) -> dict[str, Any]:
    """Re-number ``cite_id`` to 1..N in display order and rebuild ``references``.

    Display order = section order × within-section order (what the frontend
    renders). References are rebuilt from each item by construction, so the
    item↔reference bijection holds no matter how the LLM ordered things;
    ``{{cite:N}}`` placeholders and ``cite_refs`` in lead/strategy are remapped.
    Mutates and returns ``doc``.
    """

    items_by_id = {it["id"]: it for it in doc.get("items", [])}
    order: list[str] = []
    seen: set[str] = set()
    for sec in doc.get("sections", []):
        for iid in sec.get("items", []):
            if iid in items_by_id and iid not in seen:
                seen.add(iid)
                order.append(iid)
    for it in doc.get("items", []):  # any item not placed in a section
        if it["id"] not in seen:
            seen.add(it["id"])
            order.append(it["id"])

    old_to_new: dict[int, int] = {}
    references: list[dict[str, Any]] = []
    for new_cite, iid in enumerate(order, start=1):
        it = items_by_id[iid]
        old = it.get("cite_id")
        if isinstance(old, int):
            old_to_new[old] = new_cite
        it["cite_id"] = new_cite
        ref: dict[str, Any] = {
            "cite_id": new_cite,
            "title": it["title"],
            "source_domain": it["source_domain"],
            "date": it["date"],
            "url": it["url"],
        }
        if it.get("source_tier"):
            ref["source_tier"] = it["source_tier"]
        if it.get("tier_label"):
            ref["tier_label"] = it["tier_label"]
        references.append(ref)
    doc["references"] = references

    def _remap(text: str) -> str:
        return _CITE_RE.sub(
            lambda m: "{{cite:%d}}" % old_to_new.get(int(m.group(1)), int(m.group(1))),
            text or "",
        )

    lead = doc.get("lead")
    if isinstance(lead, dict):
        if "text" in lead:
            lead["text"] = _remap(lead["text"])
        if isinstance(lead.get("cite_refs"), list):
            lead["cite_refs"] = [old_to_new.get(n, n) for n in lead["cite_refs"]]
    strat = doc.get("strategy")
    if isinstance(strat, dict):
        if strat.get("body"):
            strat["body"] = _remap(strat["body"])
        if isinstance(strat.get("cite_refs"), list):
            strat["cite_refs"] = [old_to_new.get(n, n) for n in strat["cite_refs"]]
        if isinstance(strat.get("paras"), list):
            strat["paras"] = [[p[0], _remap(p[1])] for p in strat["paras"]]
    for ins in doc.get("insights") or []:
        if not isinstance(ins, dict):
            continue
        if ins.get("body"):
            ins["body"] = _remap(ins["body"])
        if isinstance(ins.get("cite_refs"), list):
            ins["cite_refs"] = [old_to_new.get(n, n) for n in ins["cite_refs"]]
    return doc


def _apply_resurface_badges(doc: dict[str, Any], reasons: dict[str, str]) -> None:
    """Prepend a turning-point badge to items whose selection reason is a
    re-surface (keyed by url). Uses the optional, already-rendered badges field."""

    for it in doc.get("items", []):
        badge = _REASON_BADGE.get(reasons.get(it.get("url"), ""))
        if badge:
            badges = list(it.get("badges") or [])
            if badge not in badges:
                it["badges"] = [badge] + badges


def _strip_unresolved_cites(doc: dict[str, Any]) -> None:
    """Remove {{cite:N}} / cite_refs entries whose N is not a real reference.

    LLM lead/strategy text often cites numbers that don't line up with the
    emitted items; rather than fail, drop the dangling placeholders so the
    report stays valid and integrity holds.
    """
    ref_set = {r.get("cite_id") for r in doc.get("references", [])}

    def _fix(text: str) -> str:
        return _CITE_RE.sub(
            lambda m: m.group(0) if int(m.group(1)) in ref_set else "", text or ""
        )

    lead = doc.get("lead")
    if isinstance(lead, dict):
        if "text" in lead:
            lead["text"] = _fix(lead["text"])
        if isinstance(lead.get("cite_refs"), list):
            lead["cite_refs"] = [n for n in lead["cite_refs"] if n in ref_set]
    strat = doc.get("strategy")
    if isinstance(strat, dict):
        if strat.get("body"):
            strat["body"] = _fix(strat["body"])
        if isinstance(strat.get("cite_refs"), list):
            strat["cite_refs"] = [n for n in strat["cite_refs"] if n in ref_set]
        if isinstance(strat.get("paras"), list):
            strat["paras"] = [[p[0], _fix(p[1])] for p in strat["paras"] if len(p) == 2]
    for ins in doc.get("insights") or []:
        if not isinstance(ins, dict):
            continue
        if ins.get("body"):
            ins["body"] = _fix(ins["body"])
        if isinstance(ins.get("cite_refs"), list):
            ins["cite_refs"] = [n for n in ins["cite_refs"] if n in ref_set]


def _prune_to_cited(doc: dict[str, Any], report_type: str) -> None:
    """Synthesized mode: keep only items actually cited (by an insight, the lead,
    or strategy) so ``references`` == the sources the report draws on (the
    academic-citation model). Rebuilds sections + renumbers cite_ids 1..M.

    Safeguard: if nothing is cited, keep the full pool (never empty the report).
    """
    used: set[int] = set()
    lead = doc.get("lead") or {}
    used |= _cites_in(lead.get("text", ""))
    used |= {n for n in (lead.get("cite_refs") or []) if isinstance(n, int)}
    strat = doc.get("strategy")
    if isinstance(strat, dict):
        used |= _cites_in(strat.get("body", ""))
        for p in strat.get("paras") or []:
            if len(p) > 1:
                used |= _cites_in(p[1])
        used |= {n for n in (strat.get("cite_refs") or []) if isinstance(n, int)}
    for ins in doc.get("insights") or []:
        used |= _cites_in(ins.get("body", ""))
        used |= {n for n in (ins.get("cite_refs") or []) if isinstance(n, int)}

    items = doc.get("items", [])
    kept = [it for it in items if it.get("cite_id") in used]
    if not kept or len(kept) == len(items):
        return
    doc["items"] = kept
    doc["sections"] = _assemble_sections(kept, report_type, doc.get("insights") or [])
    assign_cite_ids(doc)
    _strip_unresolved_cites(doc)


def _assert_citation_integrity(doc: dict[str, Any]) -> None:
    """Enforce cite_id ↔ reference ↔ superscript integrity.

    * every ``references[].cite_id`` is unique,
    * the set of item ``cite_id`` equals the set of reference ``cite_id``,
    * every ``{{cite:N}}`` in lead/strategy resolves to a reference.
    """

    ref_ids = [r["cite_id"] for r in doc["references"]]
    if len(ref_ids) != len(set(ref_ids)):
        raise ValueError("duplicate cite_id in references")
    ref_set = set(ref_ids)

    item_ids = {it["cite_id"] for it in doc["items"]}
    if item_ids != ref_set:
        raise ValueError(
            f"item cite_id set {sorted(item_ids)} != reference set {sorted(ref_set)}"
        )

    import re

    def _refs_in(text: str) -> set[int]:
        return {int(m) for m in re.findall(r"\{\{cite:(\d+)\}\}", text or "")}

    used = _refs_in(doc["lead"]["text"])
    strat = doc.get("strategy")
    if strat:
        used |= _refs_in(strat.get("body", ""))
        for para in strat.get("paras") or []:
            used |= _refs_in(para[1])
    for ins in doc.get("insights") or []:
        used |= _refs_in(ins.get("body", ""))
        used |= {n for n in (ins.get("cite_refs") or []) if isinstance(n, int)}
    missing = used - ref_set
    if missing:
        raise ValueError(f"unresolvable {{{{cite:N}}}} references: {sorted(missing)}")


def default_generated_at() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def refinalize(doc: dict[str, Any], *, report_type: str | None = None) -> dict[str, Any]:
    """Re-finalize a hand/LLM-edited report into a contract-valid doc.

    The admin review console lets an operator (or the LLM) restructure a report
    — drop/reorder/edit items. This rebuilds the engine-owned structure from the
    (edited) item list so the result stays consistent: prune stray keys, ensure
    every item has an id/subject/impact, re-assemble the cadence's sections from
    item subjects, re-number ``cite_id`` 1..N in display order + rebuild
    ``references``, and drop any now-dangling ``{{cite:N}}``. Caller recomputes
    stats/tally (trend) and validates against the schema.
    """

    doc = _clean_to_schema(dict(doc))
    rtype = report_type or doc.get("type") or "daily"
    items = doc.get("items") or []
    for idx, it in enumerate(items):
        it["id"] = it.get("id") or f"i{idx + 1}"
        it.setdefault("subject", _SUBJECT_BY_SOURCE.get(it.get("source"), "competitor"))
        it.setdefault(
            "omada_impact", _DEFAULT_IMPACT_BY_SUBJECT.get(it["subject"], "unknown")
        )
    doc["items"] = items
    insights = doc.get("insights") or []
    doc["sections"] = _assemble_sections(items, rtype, insights)
    doc = assign_cite_ids(doc)
    _strip_unresolved_cites(doc)
    if insights:
        _prune_to_cited(doc, rtype)
    return doc
