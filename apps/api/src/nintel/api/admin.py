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

import hmac
import json
import re
import time
from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException

from ..config import get_settings
from ..contract import validate_against_schema
from ..review import gate

_CITE = re.compile(r"\{\{cite:(\d+)\}\}")


# Brute-force guard: module-level consecutive-failure counter (per-process).
# Per-IP limiting is pointless here — all traffic arrives via the Cloudflare
# tunnel, so every request shares the tunnel's local source address.
_FAIL_MAX = 10
_LOCKOUT_SECONDS = 30.0
_fail_count = 0
_locked_until = 0.0


def _require_admin(token: str | None) -> None:
    global _fail_count, _locked_until
    if time.monotonic() < _locked_until:
        raise HTTPException(status_code=429, detail="too many failed auth attempts; retry later")
    expected = get_settings().admin_password
    if not token or not hmac.compare_digest(token.encode("utf-8"), expected.encode("utf-8")):
        _fail_count += 1
        if _fail_count >= _FAIL_MAX:
            _fail_count = 0
            _locked_until = time.monotonic() + _LOCKOUT_SECONDS
        raise HTTPException(status_code=401, detail="unauthorized")
    _fail_count = 0


def _pending_path(report_id: str):
    return get_settings().pending_dir / f"{report_id}.json"


def _load_pending(report_id: str) -> dict[str, Any] | None:
    path = _pending_path(report_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


_SNAPSHOT_KEEP = 20


def _write_pending(report_id: str, doc: dict[str, Any]) -> None:
    path = _pending_path(report_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        # Disk-level insurance against a bad overwrite: keep the last N drafts
        # under pending/.history/{id}/ (a subdir, so list_pending's *.json glob
        # never sees them). No restore UI yet — operators can recover by hand.
        from datetime import datetime

        hist = path.parent / ".history" / report_id
        hist.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S_%f")
        (hist / f"{stamp}.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        for old in sorted(hist.glob("*.json"))[:-_SNAPSHOT_KEEP]:
            old.unlink()
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
        doc: dict[str, Any] | None = Body(None, embed=True),
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        _require_admin(x_admin_token)
        pending = _load_pending(report_id)
        if pending is None:
            raise HTTPException(status_code=404, detail=f"no pending report '{report_id}'")
        if not get_settings().llm_enabled:
            raise HTTPException(status_code=503, detail="LLM disabled (set NINTEL_LLM_ENABLED=true)")
        from ..engine import llm

        # The client may send its (unsaved) working copy so the LLM builds on it;
        # otherwise revise the saved pending doc.
        base = pending
        if doc is not None:
            try:
                base = _finalize_edited(doc, doc.get("type") or pending.get("type"))
            except Exception as exc:  # noqa: BLE001 - bad working copy is a client error
                raise HTTPException(status_code=400, detail=f"working copy invalid: {exc}")
        try:
            revised = llm.admin_edit(base, instruction)
        except Exception as exc:  # noqa: BLE001 - LLM/parse failures -> 502
            raise HTTPException(status_code=502, detail=f"llm edit failed: {exc}")
        # NO-FABRICATION (code-level): the LLM may edit/drop/reorder items but
        # never introduce one — every revised url must already exist in the base.
        allowed = {it.get("url") for it in base.get("items", [])}
        fabricated = [
            u for u in (it.get("url") for it in revised.get("items", [])) if u not in allowed
        ]
        if fabricated:
            raise HTTPException(
                status_code=422,
                detail=f"llm edit rejected: fabricated item url(s) {fabricated[:3]}",
            )
        try:
            final = _finalize_edited(revised, base.get("type"))
        except Exception as exc:  # noqa: BLE001 - validation failures -> 502
            raise HTTPException(status_code=502, detail=f"llm edit failed: {exc}")
        return final  # preview only — not persisted until the operator saves

    @router.get("/items/pool")
    def items_pool(
        q: str | None = None,
        days: int = 14,
        subject: str | None = None,
        limit: int = 30,
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        """Search the real ingested-item pool (intel_items) for additions.

        Every row here was live-ingested, so anything the operator adds from
        this list keeps NO-FABRICATION intact by construction.
        """
        _require_admin(x_admin_token)
        from datetime import date as _date, timedelta

        from sqlalchemy import select as sa_select

        from ..store.db import session_scope
        from ..store.models import IntelItemRow

        cutoff = (_date.today() - timedelta(days=max(days, 1))).isoformat()
        with session_scope() as session:
            stmt = sa_select(IntelItemRow).where(IntelItemRow.date >= cutoff)
            if subject:
                stmt = stmt.where(IntelItemRow.subject == subject)
            if q:
                stmt = stmt.where(IntelItemRow.title.ilike(f"%{q}%"))
            stmt = stmt.order_by(
                IntelItemRow.date.desc(), IntelItemRow.last_heat.desc()
            ).limit(max(1, min(limit, 100)))
            items = [
                {
                    "content_hash": r.content_hash, "title": r.title, "url": r.url,
                    "source": r.source, "source_tier": r.source_tier,
                    "subject": r.subject, "date": r.date, "state": r.state,
                    "report_count": r.report_count, "last_heat": r.last_heat,
                }
                for r in session.scalars(stmt).all()
            ]
        return {"items": items}

    @router.post("/items/draft")
    def item_draft(
        content_hash: str = Body(..., embed=True),
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        """Turn a pool row into a contract-ready draft item.

        Starts from the lossless ingest payload, backfills the promoted columns,
        and runs the classify stage to fill summary/category/signal_strength
        (Haiku when LLM is enabled, deterministic defaults otherwise). id/cite_id
        are left for ``curate.refinalize`` to assign on save.
        """
        _require_admin(x_admin_token)
        from urllib.parse import urlparse

        from sqlalchemy import select as sa_select

        from ..engine.classify import classify
        from ..store.db import session_scope
        from ..store.models import IntelItemRow

        with session_scope() as session:
            row = session.scalar(
                sa_select(IntelItemRow).where(IntelItemRow.content_hash == content_hash)
            )
            if row is None:
                raise HTTPException(status_code=404, detail=f"no pool item '{content_hash}'")
            item: dict[str, Any] = dict(row.payload or {})
            for key, val in (
                ("title", row.title), ("url", row.url), ("source", row.source),
                ("source_tier", row.source_tier), ("subject", row.subject),
                ("date", row.date),
            ):
                item.setdefault(key, val)
        if not item.get("source_domain") and item.get("url"):
            item["source_domain"] = urlparse(item["url"]).netloc.removeprefix("www.")
        item.pop("id", None)
        item.pop("cite_id", None)
        draft = classify([item])[0]
        return {"item": draft}

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

    @router.get("/published")
    def list_published(x_admin_token: str | None = Header(None)) -> dict[str, Any]:
        _require_admin(x_admin_token)
        out: list[dict[str, Any]] = []
        for rid in gate.list_published():
            doc = gate.load_published(rid)
            if doc is None:
                continue
            out.append({
                "id": rid, "type": doc.get("type"), "date": doc.get("date"),
                "title": doc.get("title"), "excerpt": _excerpt(doc),
                "item_count": len(doc.get("items", [])),
            })
        return {"published": out}

    @router.post("/published/{report_id}/unpublish")
    def unpublish(report_id: str, x_admin_token: str | None = Header(None)) -> dict[str, Any]:
        _require_admin(x_admin_token)
        try:
            out = gate.unpublish(report_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"no published report '{report_id}'")
        except FileExistsError:
            raise HTTPException(
                status_code=409, detail=f"pending draft already exists for '{report_id}'"
            )
        return {"ok": True, "pending_id": report_id, "path": str(out)}

    @router.post("/published/{report_id}/email")
    def email_report(
        report_id: str,
        mode: str = Body("draft", embed=True),
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        """Email a published report via davmail — ``mode`` is ``draft`` | ``send``.

        draft → IMAP APPEND into Drafts (review, then send by hand); send → SMTP to
        ``NINTEL_MAIL_TO``. Mirrors the ``nintel send`` CLI (shared engine.delivery).
        """
        _require_admin(x_admin_token)
        from ..contract import load_report
        from ..engine import delivery

        doc = gate.load_published(report_id)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"no published report '{report_id}'")
        try:
            result = delivery.deliver_report(load_report(doc), mode=mode, settings=get_settings())
        except delivery.MailConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except Exception as exc:  # noqa: BLE001 - davmail down / token expired -> 502
            raise HTTPException(status_code=502, detail=f"email delivery failed: {exc}")
        return {"ok": True, **result}

    @router.get("/mail-config")
    def get_mail_config(x_admin_token: str | None = Header(None)) -> dict[str, Any]:
        """Current email recipients + delivery readiness for the settings UI."""
        _require_admin(x_admin_token)
        from ..engine import mail_config

        s = get_settings()
        cfg = mail_config.load(s)
        return {
            "to": cfg["to"],
            "cc": cfg["cc"],
            "env_to": list(s.mail_to),
            "env_cc": list(s.mail_cc),
            "from": s.davmail_user or s.mail_from,
            "configured": bool((s.davmail_user or s.mail_from) and s.davmail_cipher_key),
        }

    @router.put("/mail-config")
    def put_mail_config(
        to: list[str] = Body(default=[], embed=True),
        cc: list[str] = Body(default=[], embed=True),
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        """Persist the recipient list (validated). Takes effect on the next send."""
        _require_admin(x_admin_token)
        from ..engine import mail_config

        try:
            cfg = mail_config.save(get_settings(), to=to, cc=cc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"ok": True, **cfg}

    # ------------------------------------------------------------------
    # Subscriber management (per-section subscriptions)
    # ------------------------------------------------------------------

    @router.get("/subscribers")
    def list_subscribers(x_admin_token: str | None = Header(None)) -> dict[str, Any]:
        """List all subscribers with their section preferences."""
        _require_admin(x_admin_token)
        from ..engine import subscription

        subs = subscription.load(get_settings())
        return {"subscribers": subs, "total": len(subs),
                "active": sum(1 for s in subs if s.get("active", True)),
                "valid_sections": sorted(subscription.VALID_SECTION_KEYS)}

    @router.post("/subscribers")
    def add_subscriber(
        email: str = Body(..., embed=True),
        name: str = Body(default="", embed=True),
        sections: list[str] = Body(default=[], embed=True),
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        """Add or update a subscriber.  ``sections`` empty = all sections."""
        _require_admin(x_admin_token)
        from ..engine import subscription

        try:
            saved = subscription.upsert(
                get_settings(),
                {"email": email, "name": name, "sections": sections, "active": True},
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"ok": True, "subscriber": saved}

    @router.delete("/subscribers/{email}")
    def delete_subscriber(
        email: str,
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        """Remove a subscriber entirely."""
        _require_admin(x_admin_token)
        from ..engine import subscription

        removed = subscription.remove(get_settings(), email)
        if not removed:
            raise HTTPException(status_code=404, detail=f"subscriber '{email}' not found")
        return {"ok": True, "removed": email}

    @router.patch("/subscribers/{email}")
    def patch_subscriber(
        email: str,
        active: bool | None = Body(default=None, embed=True),
        sections: list[str] | None = Body(default=None, embed=True),
        name: str | None = Body(default=None, embed=True),
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        """Partial update: toggle active, change sections, or rename."""
        _require_admin(x_admin_token)
        from ..engine import subscription

        subs = subscription.load(get_settings())
        target = next((s for s in subs if s["email"] == email.strip().lower()), None)
        if target is None:
            raise HTTPException(status_code=404, detail=f"subscriber '{email}' not found")
        if active is not None:
            target["active"] = active
        if sections is not None:
            target["sections"] = sections
        if name is not None:
            target["name"] = name.strip()
        try:
            subscription.save(get_settings(), subs)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"ok": True, "subscriber": target}

    @router.post("/published/{report_id}/email-personalized")
    def email_personalized(
        report_id: str,
        mode: str = Body("draft", embed=True),
        x_admin_token: str | None = Header(None),
    ) -> dict[str, Any]:
        """Send per-subscriber personalised emails for a published report.

        Each active subscriber receives only their subscribed sections.
        ``mode`` is ``draft`` (IMAP Drafts) | ``send`` (SMTP direct).
        """
        _require_admin(x_admin_token)
        from ..contract import load_report
        from ..engine import delivery

        doc = gate.load_published(report_id)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"no published report '{report_id}'")
        try:
            result = delivery.deliver_personalized(
                load_report(doc), mode=mode, settings=get_settings()
            )
        except delivery.MailConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"email delivery failed: {exc}")
        return {"ok": True, **result}

    return router
