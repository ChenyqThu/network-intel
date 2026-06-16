"""FastAPI application — serves the report.json contract over REST.

Endpoints (prefix ``/api``):

* ``GET /api/health``                         → {status, version}
* ``GET /api/reports``                        → archive index
* ``GET /api/archive``                        → alias of /api/reports
* ``GET /api/reports/latest?type=daily|weekly`` → full report
* ``GET /api/reports/{report_id}``            → full report (contract JSON)
* ``GET /api/reports/{report_id}/email``      → rendered HTML (text/html)
* ``GET /api/items``                          → flat item stream with filters

CORS allows the web dev server (http://localhost:5173). Reports are served from
the published store, falling back to the canonical contract seeds.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Body, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..config import get_settings
from ..contract import load_report
from ..engine.render import render_email
from . import repository


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.admin_password == "Lucien2026":
        logging.getLogger(__name__).warning(
            "admin password is the default — set NINTEL_ADMIN_PASSWORD"
        )
    app = FastAPI(
        title="Network Intel API",
        version=__version__,
        description="Engine ↔ frontend contract (report.json) served over REST.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- health ------------------------------------------------------------
    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    # -- archive / reports index ------------------------------------------
    @app.get("/api/reports")
    def reports_index() -> dict[str, Any]:
        return {"reports": repository.archive_index()}

    @app.get("/api/archive")
    def archive_alias() -> dict[str, Any]:
        return {"reports": repository.archive_index()}

    # -- latest (declared before /{report_id} so it isn't shadowed) -------
    @app.get("/api/reports/latest")
    def reports_latest(
        type: str = Query("daily", pattern="^(daily|weekly)$")
    ) -> dict[str, Any]:
        doc = repository.latest_report(type)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"no {type} report available")
        return doc

    # -- single report -----------------------------------------------------
    @app.get("/api/reports/{report_id}")
    def report_detail(report_id: str) -> dict[str, Any]:
        doc = repository.get_report(report_id)
        if doc is None:
            # Distinguish "exists in archive but metadata-only" from "unknown".
            known = any(r["id"] == report_id for r in repository.archive_index())
            detail = (
                f"report '{report_id}' is metadata-only (no full report.json available)"
                if known
                else f"unknown report '{report_id}'"
            )
            raise HTTPException(status_code=404, detail=detail)
        return doc

    # -- rendered email ----------------------------------------------------
    @app.get("/api/reports/{report_id}/email")
    def report_email(report_id: str) -> Response:
        doc = repository.get_report(report_id)
        if doc is None:
            raise HTTPException(
                status_code=404,
                detail=f"no full report to render for '{report_id}'",
            )
        report = load_report(doc, schema_check=False)
        html = render_email(report)
        return Response(content=html, media_type="text/html")

    # -- public: unsubscribe from report emails ---------------------------
    @app.post("/api/unsubscribe")
    def unsubscribe(email: str = Body(..., embed=True)) -> dict[str, Any]:
        from ..engine import mail_config

        # Remove if present, but return a uniform response — never reveal whether
        # the address was subscribed (avoids membership enumeration over a public
        # endpoint).
        mail_config.unsubscribe(get_settings(), email)
        return {"ok": True}

    # -- admin review console (password-gated /api/admin/*) ---------------
    from .admin import create_admin_router

    app.include_router(create_admin_router())

    # -- flat item stream with filters ------------------------------------
    @app.get("/api/items")
    def items(
        subject: Optional[str] = None,
        source: Optional[str] = None,
        impact: Optional[str] = None,
        type: Optional[str] = Query(None, pattern="^(daily|weekly)$"),
        tier: Optional[str] = Query(None, pattern="^(official|community)$"),
        q: Optional[str] = None,
    ) -> dict[str, Any]:
        results = _collect_items(
            subject=subject, source=source, impact=impact,
            report_type=type, tier=tier, q=q,
        )
        return {"count": len(results), "items": results}

    return app


def _collect_items(
    *,
    subject: Optional[str],
    source: Optional[str],
    impact: Optional[str],
    report_type: Optional[str],
    tier: Optional[str],
    q: Optional[str],
) -> list[dict[str, Any]]:
    """Flatten items across published reports, applying filters.

    Deduped by the item's ``url`` (the same signal can appear in both the daily
    and weekly seed). Each returned item is annotated with ``report_id`` /
    ``report_type`` so the frontend can link back.
    """

    needle = q.lower().strip() if q else None
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for doc in repository.all_full_reports():
        if report_type and doc["type"] != report_type:
            continue
        for item in doc["items"]:
            if subject and item.get("subject") != subject:
                continue
            if source and item.get("source") != source:
                continue
            if impact and item.get("omada_impact") != impact:
                continue
            if tier and item.get("source_tier") != tier:
                continue
            if needle:
                hay = f"{item.get('title', '')} {item.get('summary', '')}".lower()
                if needle not in hay:
                    continue
            key = item["url"]
            if key in seen:
                continue
            seen.add(key)
            enriched = dict(item)
            enriched["report_id"] = doc["report_id"]
            enriched["report_type"] = doc["type"]
            out.append(enriched)

    out.sort(key=lambda it: it.get("date", ""), reverse=True)
    return out


app = create_app()
