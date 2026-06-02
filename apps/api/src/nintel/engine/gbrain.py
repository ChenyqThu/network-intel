"""kos / gbrain HTTP retrieval client.

Lets the RAG ``background`` collection be served by the user's kos knowledge
service (gbrain) instead of a local corpus. Protocol (see kos
EXTERNAL-CLIENTS-MCP-WIRE handoff):

* OAuth 2.1 client_credentials: ``POST {base}/token`` -> ``access_token``
  (Bearer, ~1h TTL), cached in-process.
* Query: ``POST {base}/mcp`` JSON-RPC ``tools/call`` name=``search``; the
  response is SSE-wrapped JSON-RPC whose ``result.content[0].text`` is a
  JSON-stringified ``SearchResult[]`` (``chunk_text`` / ``score`` / ``slug`` …).

Stdlib only (urllib) — no new dependency. Network calls happen only when the
RAG background backend is ``gbrain``; tests monkeypatch :func:`_http_post`.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..config import get_settings

_token_cache: dict[str, Any] = {}


def gbrain_configured() -> bool:
    s = get_settings()
    return bool(s.kos_mcp_base and s.kos_oauth_client_id and s.kos_oauth_client_secret)


@dataclass
class GbrainHit:
    text: str
    score: float
    metadata: dict[str, Any]


def _http_post(
    url: str,
    *,
    body: bytes,
    headers: dict[str, str],
    timeout: int = 120,
) -> tuple[int, str, str]:
    """POST and return (status, text, content_type). Isolated for test seams."""
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted host)
        return resp.status, resp.read().decode("utf-8", "replace"), resp.headers.get(
            "content-type", ""
        )


def reset_token_cache() -> None:
    _token_cache.clear()


def _access_token() -> str:
    s = get_settings()
    tok = _token_cache.get("access_token")
    if tok and _token_cache.get("expires_at", 0.0) > time.time() + 60:
        return tok
    form = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": s.kos_oauth_client_id,
            "client_secret": s.kos_oauth_client_secret,
            "scope": "read",
        }
    ).encode("utf-8")
    status, text, _ = _http_post(
        f"{s.kos_mcp_base}/token",
        body=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if status >= 400:
        raise RuntimeError(f"kos /token failed ({status}): {text[:200]}")
    body = json.loads(text)
    _token_cache["access_token"] = body["access_token"]
    _token_cache["expires_at"] = time.time() + int(body.get("expires_in", 3600))
    return _token_cache["access_token"]


def _parse_mcp(text: str, content_type: str) -> dict[str, Any]:
    if "text/event-stream" in content_type:
        for line in text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[len("data:"):].strip())
        raise RuntimeError("kos /mcp SSE response had no data line")
    return json.loads(text)


def search(query: str, *, k: int = 6) -> list[GbrainHit]:
    """Semantic search against kos; returns up to ``k`` hits."""
    if not gbrain_configured():
        raise RuntimeError(
            "NINTEL_KB_BACKEND=gbrain but KOS_MCP_BASE / KOS_OAUTH_CLIENT_ID / "
            "KOS_OAUTH_CLIENT_SECRET are not set."
        )
    s = get_settings()
    token = _access_token()
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": query, "limit": k}},
        }
    ).encode("utf-8")
    status, text, ctype = _http_post(
        f"{s.kos_mcp_base}/mcp",
        body=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    if status >= 400:
        raise RuntimeError(f"kos /mcp failed ({status}): {text[:200]}")
    env = _parse_mcp(text, ctype)
    if env.get("error"):
        raise RuntimeError(f"kos MCP error: {env['error']}")
    result = env.get("result") or {}
    content = (result.get("content") or [{}])[0].get("text", "[]")
    if result.get("isError"):
        raise RuntimeError(f"kos search error: {content[:200]}")
    rows = json.loads(content) if content else []
    hits: list[GbrainHit] = []
    for r in rows[:k]:
        hits.append(
            GbrainHit(
                text=r.get("chunk_text") or r.get("text") or "",
                score=float(r.get("score") or 0.0),
                metadata={
                    "collection": "background",
                    "slug": r.get("slug"),
                    "title": r.get("title"),
                    "type": r.get("type"),
                    "source_id": r.get("source_id"),
                    "date": r.get("effective_date"),
                },
            )
        )
    return hits
