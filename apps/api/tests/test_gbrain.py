"""kos/gbrain HTTP backend — OAuth token, SSE/JSON-RPC parse, rag routing.

No network: _http_post is monkeypatched with canned /token + /mcp responses.
"""

from __future__ import annotations

import json

import pytest

from nintel.config import get_settings
from nintel.engine import gbrain, rag

_RESULTS = [
    {"chunk_text": "UniFi 5G Backup adds WAN failover", "score": 0.91,
     "slug": "concepts/5g", "title": "5G Backup", "type": "concept",
     "effective_date": "2026-05-01"},
    {"chunk_text": "Omada gateway positioning notes", "score": 0.62,
     "slug": "notes/omada", "title": "Omada", "type": "note"},
]


def _canned(counter=None):
    def fake(url, *, body, headers, timeout=120):
        if url.endswith("/token"):
            if counter is not None:
                counter["token"] = counter.get("token", 0) + 1
            return 200, json.dumps(
                {"access_token": "gbrain_at_test", "expires_in": 3600, "token_type": "bearer"}
            ), "application/json"
        if url.endswith("/mcp"):
            inner = {
                "jsonrpc": "2.0", "id": "1",
                "result": {"content": [{"type": "text", "text": json.dumps(_RESULTS)}],
                           "isError": False},
            }
            return 200, f"event: message\ndata: {json.dumps(inner)}\n\n", "text/event-stream"
        raise AssertionError(f"unexpected url {url}")

    return fake


@pytest.fixture()
def kos_env(monkeypatch):
    monkeypatch.setenv("NINTEL_KB_BACKEND", "gbrain")
    monkeypatch.setenv("KOS_MCP_BASE", "http://127.0.0.1:7225")
    monkeypatch.setenv("KOS_OAUTH_CLIENT_ID", "gbrain_cl_test")
    monkeypatch.setenv("KOS_OAUTH_CLIENT_SECRET", "gbrain_cs_test")
    get_settings.cache_clear()
    gbrain.reset_token_cache()
    yield
    get_settings.cache_clear()
    gbrain.reset_token_cache()


def test_search_parses_sse_jsonrpc(monkeypatch, kos_env):
    monkeypatch.setattr(gbrain, "_http_post", _canned())
    hits = gbrain.search("5g backup", k=5)
    assert hits[0].text.startswith("UniFi 5G Backup")
    assert hits[0].score == 0.91
    assert hits[0].metadata["slug"] == "concepts/5g"


def test_access_token_is_cached(monkeypatch, kos_env):
    counter: dict = {}
    monkeypatch.setattr(gbrain, "_http_post", _canned(counter))
    gbrain.search("a")
    gbrain.search("b")
    assert counter["token"] == 1  # minted once, reused


def test_rag_retrieve_routes_background_to_gbrain(monkeypatch, kos_env):
    monkeypatch.setattr(gbrain, "_http_post", _canned())
    hits = rag.retrieve("5g backup carrier", collection=rag.COLLECTION_BACKGROUND, k=3)
    assert hits and hits[0].metadata["collection"] == "background"
    assert hits[0].text.startswith("UniFi 5G Backup")


def test_unconfigured_gbrain_raises(monkeypatch):
    monkeypatch.setenv("NINTEL_KB_BACKEND", "gbrain")
    for k in ("KOS_MCP_BASE", "KOS_OAUTH_CLIENT_ID", "KOS_OAUTH_CLIENT_SECRET"):
        monkeypatch.delenv(k, raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            gbrain.search("x")
    finally:
        get_settings.cache_clear()


# --- write flow: reports -> kos ------------------------------------------
def _sample_report():
    return {
        "report_id": "2026-06-01-daily", "type": "daily", "date": "2026-06-01",
        "title": "测试日报", "lead": {"text": "导语 {{cite:1}}", "strong": "要点"},
        "sections": [{"key": "omada_self", "title": "Omada 自身舆情", "items": ["d1"]}],
        "items": [{"id": "d1", "title": "EAP610 bug", "omada_impact": "needs_fix",
                   "summary": "升级失败", "impact_note": "建议 {{cite:1}}", "url": "https://x/1"}],
        "references": [{"cite_id": 1, "title": "r", "url": "https://x/1", "date": "2026-06-01"}],
    }


def test_report_to_markdown_frontmatter_and_body():
    md = gbrain.report_to_markdown(_sample_report())
    assert md.startswith("---")
    assert "type: source" in md and "source_of_truth: network-intel" in md
    assert "title: '测试日报'" in md
    assert "## Omada 自身舆情" in md
    assert "EAP610 bug" in md and "https://x/1" in md
    assert "{{cite:1}}" not in md and "[1]" in md  # cites converted, not raw


def test_index_report_calls_put_page(monkeypatch, kos_env):
    calls: dict = {}

    def fake_call(name, arguments):
        calls["name"], calls["args"] = name, arguments
        return {"slug": arguments.get("slug"), "status": "created_or_updated", "chunks": 3}

    monkeypatch.setattr(gbrain, "_mcp_call", fake_call)
    res = gbrain.index_report(_sample_report())
    assert calls["name"] == "put_page"
    assert calls["args"]["slug"] == "network-intel/2026-06-01-daily"
    assert calls["args"]["content"].startswith("---")
    assert res["status"] == "created_or_updated"


def test_index_report_lowercases_slug(monkeypatch, kos_env):
    captured: dict = {}
    monkeypatch.setattr(gbrain, "_mcp_call", lambda name, args: captured.update(args) or {"status": "ok"})
    gbrain.index_report({**_sample_report(), "report_id": "2026-W22-weekly"})
    assert captured["slug"] == "network-intel/2026-w22-weekly"  # uppercase W -> lowercase


def test_gate_publish_auto_pushes_to_kos(monkeypatch, kos_env):
    monkeypatch.setenv("NINTEL_KOS_PUBLISH", "true")
    get_settings.cache_clear()
    pushed: dict = {}

    def fake_call(name, arguments):
        pushed["name"], pushed["slug"] = name, arguments.get("slug")
        return {"status": "created_or_updated"}

    monkeypatch.setattr(gbrain, "_mcp_call", fake_call)
    from nintel.api import repository
    from nintel.review.gate import publish
    from nintel.store.seed import seed

    seed(reset=True)
    publish("2026-06-01-daily", doc=repository.get_report("2026-06-01-daily"))
    assert pushed.get("name") == "put_page"
    assert pushed.get("slug") == "network-intel/2026-06-01-daily"
    get_settings.cache_clear()
    seed(reset=True)
