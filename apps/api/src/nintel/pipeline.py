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
from .engine import (
    brand,
    classify,
    curate,
    ingest,
    recent_coverage,
    render,
    select,
    shortlist,
    trend,
)
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

    _as_of = as_of or date.today()
    reasons: dict[str, str] | None = None
    prefiltered: list[dict[str, Any]] | None = None  # 初筛: Python coarse pool
    selected: list[dict[str, Any]] | None = None      # 精选: Sonnet-shortlisted
    if persist_items:
        result = select.select_for_report(raw_items, report_type=report_type, as_of=_as_of)
        prefiltered, reasons = result.items, result.reasons
        selected = prefiltered

    settings = get_settings()
    use_dynamic = settings.llm_enabled and selected is not None
    if use_dynamic:
        # Sonnet 精选: value-select the wide Python 初筛 pool down to shortlist_max
        # (judges decision-relevance, not engagement). Best-effort; falls back to
        # the prefilter order on any LLM hiccup.
        selected = shortlist.shortlist(
            prefiltered, report_type=report_type, target_n=settings.shortlist_max, as_of=_as_of
        )
    pool = selected if use_dynamic else raw_items
    if use_dynamic:
        # Pull each shortlisted Source-A item's Notion page body (selftext +
        # community comments + any video transcript the monitor wrote) so classify
        # can read consensus/dissent — only the ~shortlist_max items are fetched.
        from .connectors import sentiment_monitor
        pool = sentiment_monitor.enrich_with_page_bodies(pool)
    classified = classify.classify(pool)
    # Dynamic reports get a date-derived id (daily: YYYY-MM-DD-daily, weekly:
    # YYYY-Www-weekly); offline keeps the seed id so the fixture round-trip holds.
    report_id = _dynamic_report_id(report_type, _as_of) if use_dynamic else None
    # Recent-coverage digest (live + LLM path only): distill the last few
    # published reports so curate can frame recurring macro topics as 持续/升级/拐点
    # instead of repeating them. Best-effort; reference-only (never citeable).
    recent = recent_coverage.build_digest(report_type, _as_of) if use_dynamic else None
    report = curate.curate(
        classified,
        report_type=report_type,
        report_id=report_id,
        report_date=_as_of.isoformat() if use_dynamic else None,
        reasons=reasons if use_dynamic else None,
        recent_coverage=recent,
    )

    seed_dashboard = report.dashboard if report.type == "weekly" else None
    report = trend.apply_trends(report, seed_dashboard=seed_dashboard, live=use_dynamic)

    # Weekly store-moves block (new products / price / stock changes) from the
    # UNIFI_CHANNELS Supabase store_recent_* tables — engine-owned tabular data,
    # live + source-B only (offline keeps the seed/empty store, so tests hold).
    if report_type == "weekly" and settings.connector_mode == "live" and "B" in settings.live_sources:
        report = _attach_store_moves(report, _as_of, settings)

    # Provenance funnel for the subtitle (采集 -> 初筛 -> 精选 -> 策展). Live/LLM path
    # only — offline stays byte-identical to the seed (round-trip tests).
    if use_dynamic:
        report = _attach_funnel(report, raw_items, prefiltered, selected, settings)

    # Belt-and-suspenders: the produced report must be schema-valid.
    validate_against_schema(report.dump())
    return report


# Raw source -> (funnel group key, friendly label). UniFi sources collapse into
# one "UniFi" group; everything else maps 1:1.
_FUNNEL_GROUP = {
    "reddit": ("reddit", "Reddit"),
    "youtube": ("youtube", "YouTube"),
    "x": ("x", "X"),
    "rss": ("rss", "行业 RSS"),
    "omada_community": ("omada", "Omada 社区"),
    "unifi_release": ("unifi", "UniFi"), "unifi_community": ("unifi", "UniFi"),
    "unifi_product": ("unifi", "UniFi"), "unifi_store": ("unifi", "UniFi"),
    "blog": ("unifi", "UniFi"),
}


def _attach_funnel(report, raw_items, prefiltered, shortlisted, settings):
    """Attach ``report.funnel``: a true decreasing funnel for the subtitle —
    采集(collected per source) -> 初筛(refined: Python prefilter) ->
    精选(shortlisted: Sonnet) -> 策展(curated: cited), plus the byline."""
    from .contract import load_report

    counts: dict[str, list] = {}
    for it in raw_items:
        # Gemini deep-research (provenance G) shares source="rss"; surface it as
        # its own funnel group so the premium research source is visible.
        if it.get("provenance") == "G":
            key, label = "gemini", "Gemini 深度研究"
        else:
            src = it.get("source") or "other"
            key, label = _FUNNEL_GROUP.get(src, (src, src))
        entry = counts.setdefault(key, [label, 0])
        entry[1] += 1
    collected = [
        {"key": k, "label": v[0], "count": v[1]}
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1][1])
    ]
    doc = report.dump()
    funnel: dict[str, Any] = {
        "collected": collected,
        "refined": len(prefiltered) if prefiltered is not None else len(raw_items),
        "curated": len(doc.get("items", [])),
        "byline": settings.report_byline,
        "tz": "PT",
    }
    if shortlisted is not None:
        funnel["shortlisted"] = len(shortlisted)
    doc["funnel"] = funnel
    return load_report(doc)


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


def _cmd_send(args: argparse.Namespace) -> int:
    """Email an already-published report via davmail — draft (default) or send.

    Loads the published report (so the email == what's live on the site) rather
    than rebuilding. ``--draft`` stages into Drafts for human review; ``--send``
    delivers to the recipient list. Default mode comes from ``NINTEL_MAIL_MODE``.
    """
    from .api import repository
    from .contract import load_report
    from .engine import delivery

    settings = get_settings()
    mode = "draft" if args.draft else "send" if args.send else settings.mail_mode

    doc = (
        repository.get_report(args.report_id)
        if args.report_id
        else repository.latest_report(args.type)
    )
    if not doc:
        which = args.report_id or f"latest {args.type}"
        print(f"send: no published report found ({which})", file=sys.stderr)
        return 1
    report = load_report(doc)

    try:
        result = delivery.deliver_report(report, mode=mode, settings=settings)
    except delivery.MailConfigError as e:
        print(f"send: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 - CLI boundary: fail loud with a clean message
        print(f"send: davmail delivery failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if result["mode"] == "draft":
        print(
            f"draft staged in {result['folder']!r}: {result['report_id']} "
            "— review in Outlook/OWA, then send"
        )
    else:
        print(f"sent {result['report_id']} -> {', '.join(result['to'])} ({result['message_id']})")
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

    p_send = sub.add_parser("send", help="email a published report via davmail (draft|send)")
    p_send.add_argument("--type", required=True, choices=["daily", "weekly"])
    p_send.add_argument("--report-id", default=None, help="specific report id (default: latest)")
    mode_grp = p_send.add_mutually_exclusive_group()
    mode_grp.add_argument(
        "--draft", action="store_true", help="stage into Drafts for review (default mode)"
    )
    mode_grp.add_argument(
        "--send", action="store_true", help="deliver to NINTEL_MAIL_TO now"
    )
    p_send.set_defaults(func=_cmd_send)

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
