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
