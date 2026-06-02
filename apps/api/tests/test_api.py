"""FastAPI endpoint tests via TestClient (offline)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from nintel.api.app import create_app
from nintel.store.seed import seed


@pytest.fixture(scope="module", autouse=True)
def _seeded():
    seed(reset=True)
    yield


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_reports_index_and_archive_alias(client):
    r = client.get("/api/reports")
    assert r.status_code == 200
    reports = r.json()["reports"]
    assert any(x["id"] == "2026-06-01-daily" for x in reports)
    # alias returns the same payload
    assert client.get("/api/archive").json() == r.json()


@pytest.mark.parametrize("rtype,expected", [
    ("daily", "2026-06-01-daily"),
    ("weekly", "2026-W22-weekly"),
])
def test_reports_latest(client, rtype, expected):
    r = client.get(f"/api/reports/latest?type={rtype}")
    assert r.status_code == 200
    assert r.json()["report_id"] == expected
    assert r.json()["type"] == rtype


def test_report_detail_full(client):
    r = client.get("/api/reports/2026-W22-weekly")
    assert r.status_code == 200
    doc = r.json()
    assert doc["report_id"] == "2026-W22-weekly"
    assert len(doc["items"]) == 13


def test_report_detail_metadata_only_404(client):
    # In the archive index but no full report.json -> honest 404 with a clear message.
    r = client.get("/api/reports/2026-05-30-daily")
    assert r.status_code == 404
    assert "metadata-only" in r.json()["detail"]


def test_report_detail_unknown_404(client):
    r = client.get("/api/reports/does-not-exist")
    assert r.status_code == 404
    assert "unknown" in r.json()["detail"]


def test_report_id_cannot_leak_other_contract_files(client):
    # A crafted report_id must not read sibling JSON files out of the contract
    # dir (report.schema.json / archive.json) and return them as reports.
    for rid in ("report.schema", "archive"):
        r = client.get(f"/api/reports/{rid}")
        assert r.status_code == 404, f"{rid} leaked: {r.status_code}"
        # And the email route must 404 cleanly (not 500 on a non-report doc).
        r2 = client.get(f"/api/reports/{rid}/email")
        assert r2.status_code == 404, f"{rid}/email leaked/crashed: {r2.status_code}"


def test_report_email_html(client):
    r = client.get("/api/reports/2026-06-01-daily/email")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    html = r.text
    assert "community.ui.com" in html       # citation domain
    assert "参考来源" in html                # references section
    assert "#0C6151" in html


def test_items_unfiltered(client):
    r = client.get("/api/items")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["items"])
    assert body["count"] > 0
    # enriched with report linkage
    assert all("report_id" in it for it in body["items"])


def test_items_filter_subject(client):
    r = client.get("/api/items?subject=omada_self")
    items = r.json()["items"]
    assert items
    assert all(it["subject"] == "omada_self" for it in items)


def test_items_filter_impact(client):
    r = client.get("/api/items?impact=threat")
    items = r.json()["items"]
    assert items
    assert all(it["omada_impact"] == "threat" for it in items)


def test_items_filter_source_and_tier(client):
    r = client.get("/api/items?source=reddit&tier=community")
    items = r.json()["items"]
    assert items
    assert all(it["source"] == "reddit" and it["source_tier"] == "community" for it in items)


def test_items_filter_type(client):
    r = client.get("/api/items?type=weekly")
    items = r.json()["items"]
    assert items
    assert all(it["report_type"] == "weekly" for it in items)


def test_items_search_q(client):
    r = client.get("/api/items?q=EAP610")
    items = r.json()["items"]
    assert items
    assert all("eap610" in (it["title"] + it["summary"]).lower() for it in items)


def test_items_search_no_match(client):
    r = client.get("/api/items?q=zzz_no_such_term_zzz")
    assert r.json()["count"] == 0
