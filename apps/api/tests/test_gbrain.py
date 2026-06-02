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
