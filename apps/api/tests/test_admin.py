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
