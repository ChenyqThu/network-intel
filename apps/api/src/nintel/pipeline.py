"""Pipeline orchestration: ingest → classify → curate → trend → render.

CLI::

    python -m nintel.pipeline build --type daily   [--publish]
    python -m nintel.pipeline build --type weekly  [--publish]
    python -m nintel.pipeline seed [--reset]
    python -m nintel.pipeline approve <report_id>

The default (offline) path is fully deterministic and produces a schema-valid
report content-equivalent to the canonical seed. With ``NINTEL_LLM_ENABLED=true``
the classify/curate stages route through Anthropic (Haiku + Opus with prompt
caching); everything else is unchanged.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import Any

from .config import get_settings
from .contract import Report, validate_against_schema
from .engine import brand, classify, curate, ingest, render, select, trend
from .store.db import init_db


def _dynamic_report_id(report_type: str, as_of: date) -> str:
    """Date-derived report id for live/LLM builds (offline keeps the seed id)."""
    if report_type == "weekly":
        iso = as_of.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}-weekly"
    return f"{as_of.isoformat()}-daily"


def build(
    report_type: str,
    *,
    persist_items: bool = True,
    as_of: date | None = None,
) -> Report:
    """Run the full pipeline and return a validated :class:`Report`.

    Stages:
      1. ingest   — connectors → normalized, deduped items (→ SQLite)
      2. select   — advance per-item state; pick new + re-surfaced items (WS1)
      3. classify — Haiku tier (fixture fallback): summary/category/strength
      4. curate   — Opus tier (fixture fallback): sections/impacts/lead/strategy
      5. trend    — recompute stats (+ weekly dashboard) from curated items

    Selection runs whenever state is persisted, but only feeds curate on the LLM
    path; offline curate replays the seed manifest from the full pool, so its
    output stays byte-identical regardless of selection.
    """

    if report_type not in ("daily", "weekly"):
        raise ValueError(f"--type must be daily|weekly, got {report_type!r}")

    if persist_items:
        init_db()

    raw_items = ingest.ingest(persist=persist_items, report_type=report_type)

    # LLM brand disambiguation for source-A omada_self candidates (drops items
    # merely named "Omada", e.g. the Omada E5 EV). Runs before select so noise
    # never takes an omada_self slot; no-op when llm is disabled (offline/tests).
    if get_settings().llm_enabled:
        raw_items = brand.refine_omada_subjects(raw_items, as_of=as_of or date.today())

    reasons: dict[str, str] | None = None
    selected: list[dict[str, Any]] | None = None
    if persist_items:
        result = select.select_for_report(
            raw_items, report_type=report_type, as_of=as_of or date.today()
        )
        selected, reasons = result.items, result.reasons

    settings = get_settings()
    use_dynamic = settings.llm_enabled and selected is not None
    pool = selected if use_dynamic else raw_items
    classified = classify.classify(pool)
    # Dynamic reports get a date-derived id (daily: YYYY-MM-DD-daily, weekly:
    # YYYY-Www-weekly); offline keeps the seed id so the fixture round-trip holds.
    _as_of = as_of or date.today()
    report_id = _dynamic_report_id(report_type, _as_of) if use_dynamic else None
    report = curate.curate(
        classified,
        report_type=report_type,
        report_id=report_id,
        report_date=_as_of.isoformat() if use_dynamic else None,
        reasons=reasons if use_dynamic else None,
    )

    seed_dashboard = report.dashboard if report.type == "weekly" else None
    report = trend.apply_trends(report, seed_dashboard=seed_dashboard)

    # Weekly store-moves block (new products / price / stock changes) from the
    # UNIFI_CHANNELS Supabase store_recent_* tables — engine-owned tabular data,
    # live + source-B only (offline keeps the seed/empty store, so tests hold).
    if report_type == "weekly" and settings.connector_mode == "live" and "B" in settings.live_sources:
        report = _attach_store_moves(report, _as_of, settings)

    # Belt-and-suspenders: the produced report must be schema-valid.
    validate_against_schema(report.dump())
    return report


def _attach_store_moves(report, as_of: date, settings):
    """Populate the weekly report's ``store`` block from Supabase store_recent_*.

    Best-effort: a Supabase hiccup or schema drift leaves the existing store
    block untouched rather than failing the weekly build.
    """
    from datetime import timedelta

    try:
        from .connectors.supabase import fetch_store_moves
        from .contract import load_report

        since = as_of - timedelta(days=settings.weekly_window_days)
        moves = fetch_store_moves(since)
        if moves:
            doc = report.dump()
            doc["store"] = moves
            return load_report(doc)
    except Exception:  # noqa: BLE001 - store block is a nice-to-have, never fatal
        import logging

        logging.getLogger(__name__).warning(
            "store moves unavailable; weekly store block left as-is", exc_info=True
        )
    return report


def build_and_submit(report_type: str) -> dict[str, Any]:
    """Build a report and route it through the review gate.

    Returns a small summary dict (report_id, path, review_mode).
    """

    from .review import submit

    report = build(report_type)
    path = submit(report)
    return {
        "report_id": report.report_id,
        "path": str(path),
        "review_mode": get_settings().review_mode,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _cmd_build(args: argparse.Namespace) -> int:
    if args.publish:
        # Force-publish regardless of review_mode by writing straight to published.
        from .review import publish

        report = build(args.type)
        out = publish(report.report_id, doc=report.dump())
        print(f"built + published {report.report_id} -> {out}")
    else:
        summary = build_and_submit(args.type)
        print(
            f"built {summary['report_id']} "
            f"(review_mode={summary['review_mode']}) -> {summary['path']}"
        )
    return 0


def _cmd_seed(args: argparse.Namespace) -> int:
    from .store.seed import seed

    counts = seed(reset=args.reset)
    print(f"seeded: {counts['reports']} reports, {counts['items']} items")
    return 0


def _cmd_approve(args: argparse.Namespace) -> int:
    from .review import approve

    out = approve(args.report_id)
    print(f"approved {args.report_id} -> {out}")
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    report = build(args.type, persist_items=False)
    print(render.render_email(report))
    return 0


def _cmd_kb(args: argparse.Namespace) -> int:
    from .engine import rag

    if args.kb_action == "reindex":
        res = rag.reindex_background()
        print(f"kb reindex: {res['added']} background chunks")
    elif args.kb_action == "index-history":
        from .api import repository

        total = 0
        for entry in repository.archive_index():
            doc = repository.get_report(entry["id"])
            if doc:
                total += rag.index_items(doc.get("items", []))
        print(f"kb index-history: indexed {total} items")
    elif args.kb_action == "stats":
        st = rag.stats()
        print(f"kb stats: dim={st['dim']} collections={st['collections']}")
    elif args.kb_action == "clear":
        rag.clear(args.collection)
        print(f"kb clear: {args.collection or 'all'}")
    elif args.kb_action == "push-report":
        from .api import repository
        from .engine import gbrain

        doc = repository.get_report(args.report_id) if args.report_id else None
        if not doc:
            print(f"kb push-report: no published report '{args.report_id}'")
            return 1
        res = gbrain.index_report(doc)
        status = res.get("status") if isinstance(res, dict) else res
        print(f"kb push-report {args.report_id}: {status}")
    elif args.kb_action == "push-all":
        from .api import repository
        from .engine import gbrain

        pushed = 0
        for entry in repository.archive_index():
            doc = repository.get_report(entry["id"])
            if doc:
                gbrain.index_report(doc)
                pushed += 1
        print(f"kb push-all: pushed {pushed} reports")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nintel", description="Network Intel engine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="build a report.json")
    p_build.add_argument("--type", required=True, choices=["daily", "weekly"])
    p_build.add_argument(
        "--publish", action="store_true", help="publish immediately (skip pending)"
    )
    p_build.set_defaults(func=_cmd_build)

    p_seed = sub.add_parser("seed", help="seed the DB from contract fixtures")
    p_seed.add_argument("--reset", action="store_true", help="drop + recreate tables")
    p_seed.set_defaults(func=_cmd_seed)

    p_appr = sub.add_parser("approve", help="approve a pending report")
    p_appr.add_argument("report_id")
    p_appr.set_defaults(func=_cmd_approve)

    p_render = sub.add_parser("render", help="render a report's email HTML to stdout")
    p_render.add_argument("--type", required=True, choices=["daily", "weekly"])
    p_render.set_defaults(func=_cmd_render)

    p_kb = sub.add_parser("kb", help="manage the RAG knowledge base")
    p_kb.add_argument(
        "kb_action",
        choices=["reindex", "index-history", "stats", "clear", "push-report", "push-all"],
    )
    p_kb.add_argument("--collection", default=None, help="for clear: background|history")
    p_kb.add_argument("--report-id", default=None, help="for push-report")
    p_kb.set_defaults(func=_cmd_kb)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
