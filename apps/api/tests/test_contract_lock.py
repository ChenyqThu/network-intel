"""WS7: contract lock.

The frontend is locked to report.json's REQUIRED shape. Backend evolution may
add OPTIONAL fields (right-extend) but must never change these required sets,
section keys, or item closedness without a deliberate, frontend-coordinated
change — which this test forces you to acknowledge by updating it.
"""

from __future__ import annotations

import json

from nintel.config import get_settings

# The hard contract the frontend (apps/web/src/types.ts) renders against.
REPORT_REQUIRED = {
    "report_id", "type", "date", "date_range", "generated_at",
    "lead", "sections", "items", "references", "stats",
}
ITEM_REQUIRED = {
    "id", "cite_id", "subject", "source", "source_domain", "source_tier",
    "title", "summary", "category", "omada_impact", "date", "url",
}
SECTION_KEYS = {"omada_self", "competitor", "sentiment", "industry", "store", "dashboard"}


def _schema() -> dict:
    return json.loads(get_settings().schema_path.read_text(encoding="utf-8"))


def test_report_required_fields_frozen():
    assert set(_schema()["required"]) == REPORT_REQUIRED


def test_item_required_fields_frozen():
    assert set(_schema()["$defs"]["intelItem"]["required"]) == ITEM_REQUIRED


def test_item_is_a_closed_object():
    # additionalProperties:false -> any new item field must be added to the schema
    # AND be optional to stay frontend-compatible.
    assert _schema()["$defs"]["intelItem"]["additionalProperties"] is False


def test_section_keys_enum_frozen():
    enum = _schema()["properties"]["sections"]["items"]["properties"]["key"]["enum"]
    assert set(enum) == SECTION_KEYS


def test_resurface_badge_field_available():
    # WS1 marks re-surfaced items via the optional `badges` field; guard that it
    # remains part of the contract so the feature stays schema-compatible.
    assert "badges" in _schema()["$defs"]["intelItem"]["properties"]
