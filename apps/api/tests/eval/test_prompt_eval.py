"""WS7: LLM prompt evaluation harness.

Skipped in default CI (needs NINTEL_LLM_ENABLED=true + an API key). Run on demand
to check a candidate prompt set against STRUCTURAL invariants the report must
satisfy regardless of wording — reusing the same validators the offline path
enforces. A/B by pointing NINTEL_PROMPT_DIR at a variant and re-running:

    NINTEL_LLM_ENABLED=true NINTEL_PROMPT_DIR=src/nintel/prompts/variants \\
        pytest -m eval -q
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("NINTEL_LLM_ENABLED", "false").strip().lower() not in ("1", "true", "yes", "on"),
    reason="eval requires NINTEL_LLM_ENABLED=true + ANTHROPIC_API_KEY",
)

_CITE_RE = __import__("re").compile(r"\{\{cite:(\d+)\}\}")
DAILY_SECTIONS = ["omada_self", "competitor", "sentiment", "industry"]


@pytest.mark.eval
@pytest.mark.parametrize("rtype", ["daily", "weekly"])
def test_llm_report_satisfies_contract_invariants(rtype):
    from nintel.contract import validate_against_schema
    from nintel.engine.curate import validate_subject_impact
    from nintel.pipeline import build

    doc = build(rtype, persist_items=False).dump()

    # 1. Schema-valid.
    validate_against_schema(doc)

    # 2. subject <-> impact legality for every item.
    for it in doc["items"]:
        validate_subject_impact(it)

    # 3. cite_id <-> reference bijection + resolvable placeholders.
    item_cites = {it["cite_id"] for it in doc["items"]}
    ref_cites = {r["cite_id"] for r in doc["references"]}
    assert item_cites == ref_cites
    used = {int(n) for n in _CITE_RE.findall(doc["lead"]["text"])}
    if doc.get("strategy"):
        used |= {int(n) for n in _CITE_RE.findall(doc["strategy"].get("body", ""))}
    assert used <= ref_cites

    # 4. Section contract per cadence.
    keys = [s["key"] for s in doc["sections"]]
    if rtype == "daily":
        assert keys == DAILY_SECTIONS
        assert doc.get("strategy") is None
    else:
        assert keys[0] == "omada_self" and "dashboard" in keys
        assert doc.get("strategy") and doc.get("dashboard")
