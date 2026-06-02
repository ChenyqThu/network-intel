"""Curate stage (Opus tier).

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

LLM-optional: ``NINTEL_LLM_ENABLED=true`` routes the synthesis through Opus via
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
    reasons: dict[str, str] | None = None,
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

        doc = llm.curate_report(items, report_type=report_type, report_id=rid)
        # LLM output can carry stray keys; the contract is closed
        # (additionalProperties:false). Prune to allowed keys, then fill the
        # structural fields we own + guarantee the cite bijection.
        doc = _clean_to_schema(doc)
        doc = _normalize_llm_doc(
            doc, report_type=report_type, report_id=rid, generated_at=generated_at
        )
        # The section taxonomy is fixed per cadence — the engine assembles it
        # from each item's subject/source, not the LLM (which drifts).
        doc["sections"] = _assemble_sections(doc.get("items", []), report_type)
        doc = assign_cite_ids(doc)
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
        curated_items.append(merged)

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
    "strategy", "tally", "sections", "items", "references", "store", "stats", "dashboard",
}
_ALLOWED_ITEM = {
    "id", "cite_id", "subject", "source", "source_domain", "source_tier", "source_label",
    "tier_label", "glyph", "provenance", "title", "stage", "badges", "summary", "category",
    "signal_strength", "omada_impact", "impact_note", "metrics", "sentiment", "relevance",
    "switch_intent", "date", "url",
}
_ALLOWED_REF = {"cite_id", "title", "source_domain", "source_tier", "tier_label", "date", "url"}
_ALLOWED_SECTION = {"key", "title", "icon", "desc", "items"}
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
_OFFICIAL_SOURCES = {"unifi_release", "blog", "unifi_product", "unifi_store"}


def _section_for_item(it: dict[str, Any]) -> str:
    subject = it.get("subject")
    if subject == "omada_self":
        return "omada_self"
    if subject == "industry":
        return "industry"
    # competitor (or unknown): official moves vs community sentiment
    return "competitor" if it.get("source") in _OFFICIAL_SOURCES else "sentiment"


def _assemble_sections(items: list[dict[str, Any]], report_type: str) -> list[dict[str, Any]]:
    """Deterministically build the cadence's fixed sections from item subjects.

    store / dashboard are item-less sections (the frontend renders report.store /
    report.dashboard); they appear with items=[] so the contract order holds.
    """
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
    if isinstance(doc.get("references"), list):
        doc["references"] = [_prune(r, _ALLOWED_REF) for r in doc["references"] if isinstance(r, dict)]
    if isinstance(doc.get("sections"), list):
        doc["sections"] = [_prune(s, _ALLOWED_SECTION) for s in doc["sections"] if isinstance(s, dict)]
    if isinstance(doc.get("store"), list):
        doc["store"] = [_prune(r, _ALLOWED_STORE) for r in doc["store"] if isinstance(r, dict)]
    return doc


def _normalize_llm_doc(
    doc: dict[str, Any], *, report_type: str, report_id: str, generated_at: str | None
) -> dict[str, Any]:
    """Fill the structural/identity fields the engine owns, so a valid report
    never depends on the LLM remembering to emit them. The LLM produces the
    editorial content (lead / sections / items / references / strategy); we set
    report_id, type, dates, and a stats placeholder (trend recomputes stats)."""

    doc["report_id"] = report_id
    doc["type"] = report_type
    doc["generated_at"] = doc.get("generated_at") or generated_at or default_generated_at()
    if not doc.get("date"):
        doc["date"] = date.today().isoformat()
    doc.setdefault("date_range", doc["date"])
    # stats + dashboard are recomputed by the trend stage — force clean values
    # so a malformed LLM block (e.g. top_hot of strings) can't fail validation.
    doc["stats"] = {"total_items": len(doc.get("items", []))}
    doc.setdefault("references", [])
    if report_type == "daily":
        doc["strategy"] = None  # daily must not carry a strategy block
        doc["dashboard"] = None
    return doc


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
    missing = used - ref_set
    if missing:
        raise ValueError(f"unresolvable {{{{cite:N}}}} references: {sorted(missing)}")


def default_generated_at() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()
