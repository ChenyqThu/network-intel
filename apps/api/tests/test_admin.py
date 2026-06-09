"""Admin review-console API tests (offline, via TestClient)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from nintel.api.app import create_app

PW = "Lucien2026"
H = {"X-Admin-Token": PW}


@pytest.fixture()
def client():
    return TestClient(create_app())


@pytest.fixture()
def pending_id():
    """A freshly-submitted pending weekly (review_mode=manual via conftest)."""
    from nintel.pipeline import build
    from nintel.review import gate
    from nintel.store.db import init_db

    init_db()  # publish() upserts the reports table, so it must exist
    rep = build("weekly", persist_items=False)
    gate.submit(rep)  # manual mode -> writes to pending/
    yield rep.report_id
    gate.reject(rep.report_id)  # cleanup if a test left it pending


def test_admin_endpoints_require_token(client, pending_id):
    assert client.get("/api/admin/pending").status_code == 401
    assert client.get(f"/api/admin/pending/{pending_id}").status_code == 401
    assert client.get("/api/admin/pending", headers={"X-Admin-Token": "nope"}).status_code == 401


def test_login_validates_password(client):
    assert client.post("/api/admin/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/admin/login", json={"password": PW}).json()["ok"] is True


def test_list_and_get_pending(client, pending_id):
    body = client.get("/api/admin/pending", headers=H).json()
    entry = next((p for p in body["pending"] if p["id"] == pending_id), None)
    assert entry is not None
    assert entry["type"] == "weekly" and entry["item_count"] > 0
    assert "{{cite" not in entry["excerpt"]  # excerpt strips cite markers
    doc = client.get(f"/api/admin/pending/{pending_id}", headers=H).json()
    assert doc["report_id"] == pending_id


def test_save_edit_revalidates_and_persists(client, pending_id):
    doc = client.get(f"/api/admin/pending/{pending_id}", headers=H).json()
    doc["lead"]["text"] = "编辑后的导语。" + (doc["lead"].get("text") or "")
    r = client.put(f"/api/admin/pending/{pending_id}", json=doc, headers=H)
    assert r.status_code == 200
    saved = r.json()
    assert saved["lead"]["text"].startswith("编辑后的导语。")
    cids = [it["cite_id"] for it in saved["items"]]
    assert cids == list(range(1, len(cids) + 1))  # contiguous
    # persisted: re-GET reflects the edit
    again = client.get(f"/api/admin/pending/{pending_id}", headers=H).json()
    assert again["lead"]["text"].startswith("编辑后的导语。")


def test_save_dropping_item_renumbers_cites_and_refs(client, pending_id):
    doc = client.get(f"/api/admin/pending/{pending_id}", headers=H).json()
    n0 = len(doc["items"])
    assert n0 >= 2
    doc["items"] = doc["items"][1:]  # drop the first item (restructure)
    saved = client.put(f"/api/admin/pending/{pending_id}", json=doc, headers=H).json()
    assert len(saved["items"]) == n0 - 1
    cids = [it["cite_id"] for it in saved["items"]]
    assert cids == list(range(1, len(cids) + 1))  # renumbered 1..N-1
    assert len(saved["references"]) == len(saved["items"])  # references rebuilt


def test_llm_edit_disabled_returns_503(client, pending_id):
    r = client.post(
        f"/api/admin/pending/{pending_id}/llm-edit",
        json={"instruction": "把导语改犀利点"}, headers=H,
    )
    assert r.status_code == 503  # llm off in tests


def test_llm_edit_uses_client_doc_as_base(client, pending_id, monkeypatch):
    from nintel.config import get_settings
    from nintel.engine import llm

    monkeypatch.setenv("NINTEL_LLM_ENABLED", "true")
    get_settings.cache_clear()
    try:
        doc = client.get(f"/api/admin/pending/{pending_id}", headers=H).json()
        doc["lead"]["text"] = "工作副本导语。" + (doc["lead"].get("text") or "")
        # echo LLM: returns its input — the response must reflect the unsaved
        # client working copy, not the pending file on disk
        monkeypatch.setattr(llm, "admin_edit", lambda base, instr: dict(base))
        r = client.post(
            f"/api/admin/pending/{pending_id}/llm-edit",
            json={"instruction": "x", "doc": doc}, headers=H,
        )
        assert r.status_code == 200
        assert r.json()["lead"]["text"].startswith("工作副本导语。")
    finally:
        get_settings.cache_clear()


def test_llm_edit_rejects_fabricated_urls(client, pending_id, monkeypatch):
    import json as _json

    from nintel.config import get_settings
    from nintel.engine import llm

    monkeypatch.setenv("NINTEL_LLM_ENABLED", "true")
    get_settings.cache_clear()
    try:
        def fabricate(base, instr):
            out = _json.loads(_json.dumps(base))
            out["items"].append(
                {**out["items"][0], "id": "zz", "url": "https://fake.example/new"}
            )
            return out

        monkeypatch.setattr(llm, "admin_edit", fabricate)
        r = client.post(
            f"/api/admin/pending/{pending_id}/llm-edit",
            json={"instruction": "x"}, headers=H,
        )
        assert r.status_code == 422
        assert "fabricated" in r.json()["detail"]
    finally:
        get_settings.cache_clear()


@pytest.fixture()
def pool_rows():
    """Two real-shaped intel_items rows: one fresh, one stale (40d old)."""
    from datetime import date, timedelta

    from nintel.store.db import init_db, session_scope
    from nintel.store.models import IntelItemRow

    init_db()
    fresh_date = date.today().isoformat()
    stale_date = (date.today() - timedelta(days=40)).isoformat()
    rows = [
        IntelItemRow(
            content_hash=f"poolhash-{i}", item_id=f"p{i}", subject="competitor",
            source="reddit", source_tier="community", category="sentiment",
            omada_impact="competitive_threat", title=title, url=f"https://pool.example/{i}",
            date=d, last_heat=heat,
            payload={
                "title": title, "url": f"https://pool.example/{i}", "source": "reddit",
                "source_domain": "pool.example", "source_tier": "community",
                "subject": "competitor", "date": d, "summary": f"摘要 {i}",
            },
        )
        for i, (title, d, heat) in enumerate([
            ("UniFi outage megathread", fresh_date, 9.0),
            ("Old UniFi rumor", stale_date, 1.0),
        ])
    ]
    with session_scope() as session:
        for r in rows:
            session.add(r)
    yield
    with session_scope() as session:
        for r in session.query(IntelItemRow).filter(
            IntelItemRow.content_hash.like("poolhash-%")
        ):
            session.delete(r)


def test_items_pool_filters_and_shape(client, pool_rows):
    body = client.get("/api/admin/items/pool", headers=H).json()
    hashes = {it["content_hash"] for it in body["items"]}
    assert "poolhash-0" in hashes  # fresh row within default 14d window
    assert "poolhash-1" not in hashes  # 40d-old row filtered out
    entry = next(it for it in body["items"] if it["content_hash"] == "poolhash-0")
    assert entry["url"] == "https://pool.example/0" and entry["subject"] == "competitor"
    # text query narrows by title
    body = client.get("/api/admin/items/pool", params={"q": "outage"}, headers=H).json()
    assert {it["content_hash"] for it in body["items"]} >= {"poolhash-0"}
    body = client.get("/api/admin/items/pool", params={"q": "nomatch-xyz"}, headers=H).json()
    assert all("poolhash" not in it["content_hash"] for it in body["items"])


def test_item_draft_is_contract_ready(client, pool_rows):
    r = client.post(
        "/api/admin/items/draft", json={"content_hash": "poolhash-0"}, headers=H
    )
    assert r.status_code == 200
    item = r.json()["item"]
    # classify (offline) backfills category/signal_strength; payload had summary
    assert item["summary"] == "摘要 0"
    assert item["category"] and item["signal_strength"]
    assert item["source_domain"] == "pool.example"
    assert "id" not in item and "cite_id" not in item  # engine assigns on save
    assert client.post(
        "/api/admin/items/draft", json={"content_hash": "nope"}, headers=H
    ).status_code == 404


def test_publish_moves_pending_to_published(client, pending_id):
    r = client.post(f"/api/admin/pending/{pending_id}/publish", headers=H)
    assert r.status_code == 200 and r.json()["ok"] is True
    ids = {p["id"] for p in client.get("/api/admin/pending", headers=H).json()["pending"]}
    assert pending_id not in ids  # no longer pending
    assert client.get(f"/api/reports/{pending_id}").status_code == 200  # now published


def test_reject_removes_pending(client, pending_id):
    assert client.post(f"/api/admin/pending/{pending_id}/reject", headers=H).status_code == 200
    ids = {p["id"] for p in client.get("/api/admin/pending", headers=H).json()["pending"]}
    assert pending_id not in ids


def test_unpublish_roundtrip(client, pending_id):
    from sqlalchemy import select as sa_select

    from nintel.store.db import session_scope
    from nintel.store.models import ItemReportRow

    def _junction_count() -> int:
        with session_scope() as session:
            rows = session.scalars(
                sa_select(ItemReportRow).where(ItemReportRow.report_id == pending_id)
            ).all()
            return len(rows)

    # publish, then pull back for re-review
    assert client.post(f"/api/admin/pending/{pending_id}/publish", headers=H).status_code == 200
    n_junction = _junction_count()
    pub = client.get("/api/admin/published", headers=H).json()["published"]
    assert pending_id in {p["id"] for p in pub}
    r = client.post(f"/api/admin/published/{pending_id}/unpublish", headers=H)
    assert r.status_code == 200
    # back in pending; published version still live for the public site
    ids = {p["id"] for p in client.get("/api/admin/pending", headers=H).json()["pending"]}
    assert pending_id in ids
    assert client.get(f"/api/reports/{pending_id}").status_code == 200
    # second unpublish refuses to clobber the pending draft
    assert client.post(f"/api/admin/published/{pending_id}/unpublish", headers=H).status_code == 409
    assert client.post("/api/admin/published/nope/unpublish", headers=H).status_code == 404
    # edit + re-publish overwrites the live version; junction stays idempotent
    doc = client.get(f"/api/admin/pending/{pending_id}", headers=H).json()
    doc["lead"]["text"] = "重审后的导语。" + (doc["lead"].get("text") or "")
    assert client.put(f"/api/admin/pending/{pending_id}", json=doc, headers=H).status_code == 200
    assert client.post(f"/api/admin/pending/{pending_id}/publish", headers=H).status_code == 200
    assert _junction_count() == n_junction  # no duplicate item↔report rows
    live = client.get(f"/api/reports/{pending_id}").json()
    assert live["lead"]["text"].startswith("重审后的导语。")


def test_save_writes_bounded_snapshots(client, pending_id):
    import shutil

    from nintel.config import get_settings

    hist = get_settings().pending_dir / ".history" / pending_id
    shutil.rmtree(hist, ignore_errors=True)  # earlier tests' saves also snapshot
    doc = client.get(f"/api/admin/pending/{pending_id}", headers=H).json()
    for i in range(3):
        doc["lead"]["text"] = f"第{i}版导语。"
        assert client.put(f"/api/admin/pending/{pending_id}", json=doc, headers=H).status_code == 200
    snaps = sorted(hist.glob("*.json"))
    assert len(snaps) == 3  # one snapshot per overwrite (the pre-save state)
    # snapshots are hidden from the pending list
    ids = {p["id"] for p in client.get("/api/admin/pending", headers=H).json()["pending"]}
    assert ids == {pending_id}
    shutil.rmtree(hist, ignore_errors=True)
