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
from .engine import classify, curate, ingest, render, select, trend
from .store.db import init_db


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

    raw_items = ingest.ingest(persist=persist_items)

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
    report = curate.curate(
        classified,
        report_type=report_type,
        reasons=reasons if use_dynamic else None,
    )

    seed_dashboard = report.dashboard if report.type == "weekly" else None
    report = trend.apply_trends(report, seed_dashboard=seed_dashboard)

    # Belt-and-suspenders: the produced report must be schema-valid.
    validate_against_schema(report.dump())
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
        "kb_action", choices=["reindex", "index-history", "stats", "clear"]
    )
    p_kb.add_argument("--collection", default=None, help="for clear: background|history")
    p_kb.set_defaults(func=_cmd_kb)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
