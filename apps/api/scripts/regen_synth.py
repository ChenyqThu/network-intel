"""Regenerate the daily (06-02) + weekly (W22) with the SYNTHESIS pipeline
(insights + funnel + non-empty lead), from REAL live data.

Two-phase so we never mutate the main DB's select state:
  Phase A — build both reports against a throwaway temp state DB (fresh
            eligibility, so the prior run's cooldown doesn't suppress items).
  Phase B — publish the finished docs to the MAIN DB via the normal publish path
            (upsert reports + write data/published/<id>.json).

Run from apps/api:  .venv/bin/python scripts/regen_synth.py
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# --- load .env (shell live/LLM flags take precedence) ------------------------
for _line in Path(".env").read_text().splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        os.environ[_k] = _v

os.environ["NINTEL_CONNECTOR_MODE"] = "live"
os.environ["NINTEL_LIVE_SOURCES"] = "A,B,C,G"
os.environ["NINTEL_LLM_ENABLED"] = "true"
os.environ["NINTEL_SELECT_MAX_ITEMS_DAILY"] = "12"
# RAG: pull Omada/competitor/industry background from the kos knowledge base so
# the curator's research is grounded. background -> kos (gbrain); history stays
# local (hash embedder = no model download; history is empty on a fresh run).
os.environ["NINTEL_RAG_ENABLED"] = "true"
os.environ["NINTEL_KB_BACKEND"] = "gbrain"
os.environ.setdefault("NINTEL_EMBEDDER", "hash")

MAIN_DB = str((Path("data") / "nintel.db").resolve())
TMP_DB = "/tmp/nintel_regen.db"
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)

from nintel.config import get_settings  # noqa: E402
from nintel.engine.select import SelectConfig, is_fresh  # noqa: E402
from nintel.pipeline import build  # noqa: E402
from nintel.review.gate import publish  # noqa: E402
from nintel.store.db import init_db  # noqa: E402

JOBS = [
    ("weekly", date(2026, 5, 31)),  # W22 = 05-25..05-31
    ("daily", date(2026, 6, 2)),    # 06-02 = 06-01..06-02
]

# --- Phase A: build against a fresh temp state DB ----------------------------
os.environ["NINTEL_DB_PATH"] = TMP_DB
get_settings.cache_clear()
s = get_settings()
assert s.llm_enabled, "llm not enabled"
assert s.connector_mode == "live", f"mode={s.connector_mode!r}"
assert os.environ.get("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY missing"
print(f"settings OK: live={os.environ['NINTEL_LIVE_SOURCES']} base_url={s.anthropic_base_url}")
print(f"temp state db: {TMP_DB}\n")
init_db()
cfg = SelectConfig.from_settings(s)

built = []
for rtype, as_of in JOBS:
    print(f"{'='*72}\nBUILD {rtype} as_of={as_of}\n{'='*72}")
    rep = build(rtype, as_of=as_of)
    doc = rep.dump()
    items = doc.get("items", [])
    window = cfg.window_days(rtype)
    # provenance-G (deep-research) items are freshness-exempt by design: they are
    # period syntheses citing authoritative sources of any date (matches the
    # select-stage rule). Only non-G items must fall inside the report window.
    stale = [
        it
        for it in items
        if it.get("provenance") != "G" and not is_fresh(it.get("date"), as_of, window)
    ]
    assert not stale, "STALE LEAKED:\n" + "\n".join(
        f"  {it.get('date')} {it.get('source')} {it.get('url')}" for it in stale
    )
    ins = doc.get("insights") or []
    fn = doc.get("funnel") or {}
    print(f"  report_id={doc['report_id']} items={len(items)} insights={len(ins)}")
    print(f"  funnel: collected={[ (c['label'],c['count']) for c in fn.get('collected',[]) ]}"
          f" refined={fn.get('refined')} curated={fn.get('curated')} byline={fn.get('byline')!r}")
    print(f"  lead: {doc['lead'].get('text','')[:90]!r}")
    for i, x in enumerate(ins):
        print(f"    insight[{i}] [{x['subject']}] {x['title'][:50]!r} cite_refs={x.get('cite_refs')}")
    assert ins, f"NO INSIGHTS produced for {rtype} — synthesis prompt not honored"
    assert (doc['lead'].get('text') or '').strip(), f"EMPTY LEAD for {rtype}"
    built.append(doc)

# --- Phase B: publish to the MAIN db -----------------------------------------
print(f"\n{'='*72}\nPUBLISH -> main db ({MAIN_DB})\n{'='*72}")
os.environ["NINTEL_DB_PATH"] = MAIN_DB
get_settings.cache_clear()
init_db()
for doc in built:
    out = publish(doc["report_id"], doc=doc)
    print(f"  published {doc['report_id']} -> {out}")

print("\n=== DONE ===")
