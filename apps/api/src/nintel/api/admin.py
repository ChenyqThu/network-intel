"""Admin review console API (``/api/admin/*``) — password-gated.

Lets an operator review **pending** (manual-review) reports, edit them directly
or via a free-text LLM instruction (with live preview), then publish or reject.

Auth is deliberately simple (PRD: "简单密码拦截"): every admin call must send the
``X-Admin-Token`` header equal to ``settings.admin_password`` (default
``Lucien2026``, override via ``NINTEL_ADMIN_PASSWORD``). ``/login`` validates the
password so the UI can gate before storing it.

Editing flow: a saved/LLM-revised doc is re-finalized (``curate.refinalize`` —
rebuild sections from items, renumber cite_ids, rebuild references, drop dangling
cites), stats/tally recomputed (``trend``), and schema-validated before it is
written back to ``pending/`` or returned as a preview.
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException

from ..config import get_settings
from ..contract import validate_against_schema
from ..review import gate

_CITE = re.compile(r"\{\{cite:(\d+)\}\}")


def _require_admin(token: str | None) -> None:
    if not token or token != get_settings().admin_password:
        raise HTTPException(status_code=401, detail="unauthorized")


def _pending_path(report_id: str):
    return get_settings().pending_dir / f"{report_id}.json"


def _load_pending(report_id: str) -> dict[str, Any] | None:
    path = _pending_path(report_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_pending(report_id: str, doc: dict[str, Any]) -> None:
    path = _pending_path(report_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def _excerpt(doc: dict[str, Any]) -> str:
    lead = (doc.get("lead") or {}).get("text") or ""
    if not lead and isinstance(doc.get("strategy"), dict):
        paras = doc["strategy"].get("paras") or []
        lead = (paras[0][1] if paras and len(paras[0]) > 1 else "") or doc["strategy"].get("body", "")
    return _CITE.sub("", lead).strip()[:160]


def _finalize_edited(doc: dict[str, Any], report_type: str | None) -> dict[str, Any]:
    """Re-finalize an edited/revised doc into a schema-valid report."""
    from ..engine import curate, trend

    final = curate.refinalize(doc, report_type=report_type)
    items = final.get("items", [])
    final["stats"] = trend.compute_stats(items) if items else {"total_items": 0}
    final["tally"] = trend.compute_tally(items)
    if (report_type or final.get("type")) == "weekly" and isinstance(final.get("dashboard"), dict):
        final["dashboard"] = trend.normalize_dashboard(final["dashboard"], items, final["tally"])
    validate_against_schema(final)
    return final


def create_admin_router() -> APIRouter:
    router = APIRouter(prefix="/api/admin", tags=["admin"])

    @router.post("/login")
    def login(password: str = Body(..., embed=True)) -> dict[str, Any]:
        if password != get_settings().admin_password:
            raise HTTPException(status_code=401, detail="invalid password")
        return {"ok": True}

    @router.get("/pending")
    def list_pending(x_admin_token: str | None = Header(None)) -> dict[str, Any]:
        _require_admin(x_admin_token)
        out: list[dict[str, Any]] = []
        for rid in gate.list_pending():
            doc = _load_pending(rid)
            if doc is None:
                continue
            out.append({
                "id": rid, "type": doc.get("type"), "date": doc.get("date"),
                "title": doc.get("title"), "excerpt": _excerpt(doc),
                "item_count": len(doc.get("items", [])),
            })
        return {"pending": out}

    @router.get("/pending/{report_id}")
    def get_pending(report_id: str, x_admin_token: str | None = Header(None)) -> dict[str, Any]:
        _require_admin(x_admin_token)
        doc = _load_pending(report_id)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"no pending report '{report_id}'")
        return doc

    @router.put("/pending/{report_id}")
    def save_pending(
        report_id: str,
        doc: dict[str, Any] = Body(...),
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        _require_admin(x_admin_token)
        if _load_pending(report_id) is None:
            raise HTTPException(status_code=404, detail=f"no pending report '{report_id}'")
        try:
            final = _finalize_edited(doc, doc.get("type"))
        except Exception as exc:  # noqa: BLE001 - surface validation errors to the editor
            raise HTTPException(status_code=400, detail=f"report invalid after edit: {exc}")
        _write_pending(report_id, final)
        return final

    @router.post("/pending/{report_id}/llm-edit")
    def llm_edit(
        report_id: str,
        instruction: str = Body(..., embed=True),
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        _require_admin(x_admin_token)
        doc = _load_pending(report_id)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"no pending report '{report_id}'")
        if not get_settings().llm_enabled:
            raise HTTPException(status_code=503, detail="LLM disabled (set NINTEL_LLM_ENABLED=true)")
        from ..engine import llm

        try:
            revised = llm.admin_edit(doc, instruction)
            final = _finalize_edited(revised, doc.get("type"))
        except Exception as exc:  # noqa: BLE001 - LLM/parse/validation failures -> 502
            raise HTTPException(status_code=502, detail=f"llm edit failed: {exc}")
        return final  # preview only — not persisted until the operator saves

    @router.post("/pending/{report_id}/publish")
    def publish(report_id: str, x_admin_token: str | None = Header(None)) -> dict[str, Any]:
        _require_admin(x_admin_token)
        try:
            out = gate.approve(report_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"no pending report '{report_id}'")
        return {"ok": True, "published_id": report_id, "path": str(out)}

    @router.post("/pending/{report_id}/reject")
    def reject(report_id: str, x_admin_token: str | None = Header(None)) -> dict[str, Any]:
        _require_admin(x_admin_token)
        gate.reject(report_id)
        return {"ok": True}

    return router
