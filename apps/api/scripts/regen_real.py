"""One-off: regenerate the two reports the user asked for, from REAL live data,
with the freshness gate enforced. Builds both before publishing either so the
cross-day dedup doesn't suppress the 05-31 overlap; self-asserts every item is
inside its report window (no stale leakage) before anything is published.

    2026-06-01-daily   (window 05-31..06-01)
    2026-W22-weekly    (window 05-25..05-31)
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# --- load .env into the environment (so shell live/LLM flags take precedence) -
for _line in Path(".env").read_text().splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        os.environ[_k] = _v

os.environ["NINTEL_CONNECTOR_MODE"] = "live"
# A=Notion sentiment, B=Supabase channels+store, C=industry RSS, G=Gemini deep-
# research (weekly-only via cadence gate). H (HTML scrape) excluded: templates
# need per-site validation + title/date cleanup before production.
os.environ["NINTEL_LIVE_SOURCES"] = "A,B,C,G"
os.environ["NINTEL_LLM_ENABLED"] = "true"
os.environ["NINTEL_SELECT_MAX_ITEMS_DAILY"] = "12"

from nintel.config import get_settings  # noqa: E402

get_settings.cache_clear()
s = get_settings()
assert s.connector_mode == "live", f"connector_mode={s.connector_mode!r} (expected live)"
assert s.llm_enabled, "llm not enabled"
assert os.environ.get("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY missing"
print(f"settings OK: mode={s.connector_mode} live={os.environ['NINTEL_LIVE_SOURCES']} "
      f"llm={s.llm_enabled} base_url={s.anthropic_base_url}")
print(f"windows: daily={s.daily_window_days}d weekly={s.weekly_window_days}d\n")

from nintel.engine.select import SelectConfig, is_fresh  # noqa: E402
from nintel.pipeline import build  # noqa: E402
from nintel.review.gate import publish  # noqa: E402
from nintel.store.db import init_db  # noqa: E402

init_db()  # fresh empty schema (db file was removed for a clean slate)
cfg = SelectConfig.from_settings(s)

JOBS = [
    ("weekly", date(2026, 5, 31)),   # W22 = 05-25..05-31 (latest complete week)
    ("daily", date(2026, 6, 2)),     # 06-02 = 06-01..06-02 (latest day)
]

built = []
for rtype, as_of in JOBS:
    print(f"\n{'='*72}\nBUILD {rtype} as_of={as_of}\n{'='*72}")
    rep = build(rtype, as_of=as_of)
    doc = rep.dump()
    window = cfg.window_days(rtype)
    items = doc.get("items", [])
    by_src: dict[str, int] = {}
    for it in items:
        by_src[it.get("source", "?")] = by_src.get(it.get("source", "?"), 0) + 1
    dates = sorted(it.get("date", "") for it in items)
    print(f"  report_id={doc['report_id']} date={doc.get('date')} items={len(items)}")
    print(f"  by_source={by_src}")
    print(f"  item date range: {dates[0] if dates else '-'} -> {dates[-1] if dates else '-'}")

    # CRITICAL self-check: no stale item may leak into the report.
    stale = [it for it in items if not is_fresh(it.get("date"), as_of, window)]
    assert not stale, "STALE LEAKED:\n" + "\n".join(
        f"    {it.get('date')} {it.get('source')} {it.get('url')}" for it in stale
    )
    print(f"  ✓ all {len(items)} items within {window}d window, none in the future")
    built.append((doc, as_of, window))

# Only publish once BOTH built clean.
print(f"\n{'='*72}\nPUBLISH\n{'='*72}")
for doc, as_of, window in built:
    out = publish(doc["report_id"], doc=doc)
    print(f"  published {doc['report_id']} -> {out}")

# Sample URLs for manual verification.
print(f"\n{'='*72}\nSAMPLE URLS (manual check)\n{'='*72}")
for doc, as_of, window in built:
    print(f"\n[{doc['report_id']}]")
    for it in doc.get("items", []):
        print(f"  {it.get('date')}  {it.get('source'):<16} {it.get('url')}")

print("\n=== DONE ===")
