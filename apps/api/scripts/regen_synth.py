"""Regenerate the daily + weekly reports with the SYNTHESIS pipeline
(insights + funnel + non-empty lead), from REAL live data.

Two-phase so we never mutate the main DB's select state:
  Phase A — build the reports against a throwaway temp state DB (fresh
            eligibility, so the prior run's cooldown doesn't suppress items).
  Phase B — publish the finished docs to the MAIN DB via the normal publish path
            (upsert reports + write data/published/<id>.json).

Run from apps/api:
  .venv/bin/python scripts/regen_synth.py                          # pinned seed dates (W22 / 06-02)
  .venv/bin/python scripts/regen_synth.py --type weekly --current  # this week's weekly, live
  .venv/bin/python scripts/regen_synth.py --as-of 2026-07-01       # a specific as-of date

With no date flag the pinned seed dates are used (reproduces the canonical seed
reports); ``--current`` targets today's ISO week/day and ``--as-of`` an explicit
date. ``--type`` limits the run to just the weekly or the daily.
"""

from __future__ import annotations

import argparse
from datetime import date

# Pinned seed dates — the canonical reproducible reports (used when no date flag
# is given, so the default run stays comparable to the seeds).
PINNED: dict[str, date] = {
    "weekly": date(2026, 5, 31),  # W22 = 05-25..05-31
    "daily": date(2026, 6, 2),    # 06-02 = 06-01..06-02
}
# Run order when building both (weekly first, matching the historical script).
_ORDER = ("weekly", "daily")


def resolve_jobs(
    kinds: list[str], *, current: bool, as_of: date | None, today: date
) -> list[tuple[str, date]]:
    """``[(kind, as_of_date)]`` for the run.

    No date flag -> the pinned seed date per kind (backward-compatible). ``current``
    uses ``today`` for every kind; ``as_of`` uses that explicit date for every kind.
    ``current`` and ``as_of`` are mutually exclusive.
    """
    if current and as_of is not None:
        raise SystemExit("pass only one of --current / --as-of")
    if current:
        return [(k, today) for k in kinds]
    if as_of is not None:
        return [(k, as_of) for k in kinds]
    return [(k, PINNED[k]) for k in kinds]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Regenerate daily/weekly reports (live + synthesis).")
    p.add_argument(
        "--type", choices=["weekly", "daily", "both"], default="both",
        help="which report(s) to build (default: both)",
    )
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--current", action="store_true", help="target today's ISO week/day")
    grp.add_argument("--as-of", metavar="YYYY-MM-DD", help="target an explicit as-of date")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import os
    from pathlib import Path

    args = _parse_args(argv)
    kinds = list(_ORDER) if args.type == "both" else [args.type]
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    jobs = resolve_jobs(kinds, current=args.current, as_of=as_of, today=date.today())

    # --- load .env (its real creds override any stale shell value) -----------
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

    from nintel.config import get_settings
    from nintel.engine.select import SelectConfig, is_fresh
    from nintel.pipeline import build
    from nintel.review.gate import publish
    from nintel.store.db import init_db

    # --- Phase A: build against a fresh temp state DB ------------------------
    os.environ["NINTEL_DB_PATH"] = TMP_DB
    get_settings.cache_clear()
    s = get_settings()
    assert s.llm_enabled, "llm not enabled"
    assert s.connector_mode == "live", f"mode={s.connector_mode!r}"
    assert os.environ.get("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY missing"
    print(f"settings OK: live={os.environ['NINTEL_LIVE_SOURCES']} base_url={s.anthropic_base_url}")
    print(f"jobs: {[(k, d.isoformat()) for k, d in jobs]}")
    print(f"temp state db: {TMP_DB}\n")
    init_db()
    cfg = SelectConfig.from_settings(s)

    built = []
    for rtype, as_of_job in jobs:
        print(f"{'='*72}\nBUILD {rtype} as_of={as_of_job}\n{'='*72}")
        rep = build(rtype, as_of=as_of_job)
        doc = rep.dump()
        items = doc.get("items", [])
        window = cfg.window_days(rtype)
        # provenance-G (deep-research) items are freshness-exempt by design: they are
        # period syntheses citing authoritative sources of any date (matches the
        # select-stage rule). Only non-G items must fall inside the report window.
        stale = [
            it
            for it in items
            if it.get("provenance") != "G" and not is_fresh(it.get("date"), as_of_job, window)
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

    # --- Phase B: publish to the MAIN db -------------------------------------
    print(f"\n{'='*72}\nPUBLISH -> main db ({MAIN_DB})\n{'='*72}")
    os.environ["NINTEL_DB_PATH"] = MAIN_DB
    get_settings.cache_clear()
    init_db()
    for doc in built:
        out = publish(doc["report_id"], doc=doc)
        print(f"  published {doc['report_id']} -> {out}")

    print("\n=== DONE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
