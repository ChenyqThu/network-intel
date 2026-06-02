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
import re
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
            # Request both; the client grant is capped server-side to what it has.
            "scope": "read write",
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


def _mcp_call(name: str, arguments: dict[str, Any]) -> Any:
    """Call an MCP tool over /mcp; return the parsed (JSON-decoded) op result."""
    if not gbrain_configured():
        raise RuntimeError(
            "kos is not configured (KOS_MCP_BASE / KOS_OAUTH_CLIENT_ID / "
            "KOS_OAUTH_CLIENT_SECRET)."
        )
    s = get_settings()
    token = _access_token()
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
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
        raise RuntimeError(f"kos /mcp {name} failed ({status}): {text[:200]}")
    env = _parse_mcp(text, ctype)
    if env.get("error"):
        raise RuntimeError(f"kos MCP error ({name}): {env['error']}")
    result = env.get("result") or {}
    content = (result.get("content") or [{}])[0].get("text", "")
    if result.get("isError"):
        raise RuntimeError(f"kos {name} error: {content[:200]}")
    return json.loads(content) if content else None


def search(query: str, *, k: int = 6) -> list[GbrainHit]:
    """Semantic search against kos; returns up to ``k`` hits."""
    rows = _mcp_call("search", {"query": query, "limit": k}) or []
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


# --------------------------------------------------------------------------- #
# Write: push published reports into kos (put_page)
# --------------------------------------------------------------------------- #
_CITE_RE = re.compile(r"\{\{cite:(\d+)\}\}")


def _strip_cites(text: str) -> str:
    return _CITE_RE.sub(lambda m: f"[{m.group(1)}]", text or "")


def report_to_markdown(doc: dict[str, Any]) -> str:
    """Render a report.json doc to a kos page (YAML frontmatter + markdown body)."""
    rid = doc["report_id"]
    rtype = doc.get("type", "daily")
    rdate = doc.get("date", "")
    title = (doc.get("title") or rid).replace("'", "''")
    lead = doc.get("lead") or {}
    items = {it["id"]: it for it in doc.get("items", [])}

    out = [
        "---",
        "type: source",
        "kind: source",
        f"title: '{title}'",
        "status: published",
        f"created: '{rdate}'",
        f"updated: '{rdate}'",
        "source_of_truth: network-intel",
        "source_refs:",
        f"  - network-intel:{rid}",
        f"tags: [network-intel, {rtype}, omada-intel]",
        "---",
        "",
        f"# {doc.get('title') or rid}",
        "",
    ]
    if lead.get("strong"):
        out.append(f"**{_strip_cites(lead['strong'])}**")
        out.append("")
    if lead.get("text"):
        out.append(_strip_cites(lead["text"]))
        out.append("")

    strat = doc.get("strategy")
    if isinstance(strat, dict):
        out.append(f"## 🎯 {strat.get('title', '市场策略洞察')}")
        for para in strat.get("paras") or []:
            if isinstance(para, (list, tuple)) and len(para) == 2:
                out.append(f"**{para[0]}** {_strip_cites(para[1])}")
        if strat.get("body"):
            out.append(_strip_cites(strat["body"]))
        out.append("")

    for sec in doc.get("sections", []):
        if sec.get("key") == "dashboard":
            continue
        out.append(f"## {sec.get('title', sec.get('key', ''))}")
        for iid in sec.get("items", []):
            it = items.get(iid)
            if not it:
                continue
            out.append(f"- **{it.get('title', '')}** ({it.get('omada_impact', '')}) — {it.get('summary', '')}")
            if it.get("impact_note"):
                out.append(f"  - 研判: {_strip_cites(it['impact_note'])}")
            if it.get("url"):
                out.append(f"  - 来源: {it['url']}")
        out.append("")

    store = doc.get("store") or []
    if store:
        out.append("## Store 动向")
        for row in store:
            out.append(f"- {row.get('product', '')} — {row.get('change', '')} (stock: {row.get('stock', '')})")
        out.append("")

    refs = doc.get("references") or []
    if refs:
        out.append("## 参考来源")
        for r in refs:
            out.append(f"{r.get('cite_id')}. {r.get('title', '')} — {r.get('url', '')} ({r.get('date', '')})")
    return "\n".join(out)


def put_page(slug: str, content: str) -> Any:
    """Write a markdown page to kos under the client's bound write source."""
    return _mcp_call("put_page", {"slug": slug, "content": content})


def index_report(doc: dict[str, Any]) -> Any:
    """Push one published report into kos as a page (slug = <prefix>/<report_id>).

    The slug is lowercased: kos stores page slugs lowercased, but its addTag step
    matches the literal slug, so an uppercase id (e.g. ``2026-W22-weekly``) would
    fail with "page not found".
    """
    slug = f"{get_settings().kos_slug_prefix}/{doc['report_id']}".lower()
    return put_page(slug, report_to_markdown(doc))
