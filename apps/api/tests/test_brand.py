"""LLM brand disambiguation for source-A omada_self candidates (no network)."""

from __future__ import annotations

from datetime import date

AS_OF = date(2026, 6, 1)


def test_refine_is_noop_when_llm_disabled(monkeypatch):
    from nintel.config import get_settings
    from nintel.engine import brand

    monkeypatch.setenv("NINTEL_LLM_ENABLED", "false")
    get_settings.cache_clear()
    items = [{"subject": "omada_self", "title": "x", "date": "2026-06-01", "url": "u"}]
    assert brand.refine_omada_subjects(items, as_of=AS_OF) == items
    get_settings.cache_clear()


def test_refine_drops_other_and_reclassifies_competitor(monkeypatch):
    from nintel.config import get_settings
    from nintel.engine import brand, llm

    monkeypatch.setenv("NINTEL_LLM_ENABLED", "true")
    get_settings.cache_clear()
    items = [
        {"subject": "omada_self", "title": "OMADA E5 Pro (car)", "date": "2026-05-31",
         "url": "car", "sentiment": "pos", "omada_impact": "strength_confirm"},
        {"subject": "omada_self", "title": "Ubiquiti thing", "date": "2026-05-31",
         "url": "comp", "sentiment": "neg", "omada_impact": "needs_fix"},
        {"subject": "omada_self", "title": "TP-Link EAP225 review", "date": "2026-05-31",
         "url": "omada", "sentiment": "pos", "omada_impact": "strength_confirm"},
        {"subject": "competitor", "title": "unrelated UniFi", "date": "2026-05-31", "url": "keep"},
    ]
    # Stub the Haiku call: candidate 0 -> other, 1 -> competitor, 2 -> omada.
    monkeypatch.setattr(llm, "classify_brands", lambda subset: {0: "other", 1: "competitor", 2: "omada"})
    out = brand.refine_omada_subjects(items, as_of=AS_OF)
    urls = {it["url"] for it in out}

    assert "car" not in urls                       # 'other' dropped (the EV)
    assert {"comp", "omada", "keep"} <= urls       # the rest kept
    comp = next(it for it in out if it["url"] == "comp")
    assert comp["subject"] == "competitor" and comp["omada_impact"] == "opportunity"  # neg -> opp
    omada = next(it for it in out if it["url"] == "omada")
    assert omada["subject"] == "omada_self"        # genuine Omada kept
    get_settings.cache_clear()


def test_refine_keeps_all_on_llm_error(monkeypatch):
    from nintel.config import get_settings
    from nintel.engine import brand, llm

    monkeypatch.setenv("NINTEL_LLM_ENABLED", "true")
    get_settings.cache_clear()
    items = [{"subject": "omada_self", "title": "EAP225", "date": "2026-05-31", "url": "u"}]

    def _boom(subset):
        raise RuntimeError("haiku down")

    monkeypatch.setattr(llm, "classify_brands", _boom)
    # best-effort: a filter outage must not fail the build or drop content.
    assert brand.refine_omada_subjects(items, as_of=AS_OF) == items
    get_settings.cache_clear()
