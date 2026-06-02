"""WS5: RAG vector store — chunking, upsert, KNN, namespace filter, dim guard.

Runs offline: conftest sets NINTEL_EMBEDDER=hash and an isolated kb.db.
"""

from __future__ import annotations

from nintel.engine import rag
from nintel.engine.embeddings import get_embedder
from nintel.engine.rag import (
    COLLECTION_BACKGROUND,
    COLLECTION_HISTORY,
    VectorStore,
    _chunk_markdown,
)


def test_chunk_markdown_is_header_aware():
    chunks = _chunk_markdown("# H1\nbody one\n## H2\nbody two")
    headings = [h for h, _ in chunks]
    assert "H1" in headings and "H2" in headings
    assert any("body two" in body for _, body in chunks)


def test_upsert_and_knn_ranks_shared_tokens_first():
    rag.clear()
    emb = get_embedder()
    store = rag.get_store()
    try:
        rows = [
            {"collection": COLLECTION_BACKGROUND, "doc_id": "a", "heading": "5G",
             "content_sha": "s1", "text": "unifi 5g backup carrier select"},
            {"collection": COLLECTION_BACKGROUND, "doc_id": "b", "heading": "PoE",
             "content_sha": "s2", "text": "omada poe switch sg2218 request"},
        ]
        store.upsert(rows, emb.embed([r["text"] for r in rows]))
    finally:
        store.close()

    hits = rag.retrieve("5g backup carrier", collection=COLLECTION_BACKGROUND, k=1)
    assert hits and "5g" in hits[0].text.lower()


def test_namespace_filter_isolates_collections():
    rag.clear()
    emb = get_embedder()
    store = rag.get_store()
    try:
        store.upsert(
            [{"collection": COLLECTION_BACKGROUND, "content_sha": "bg", "text": "shared topic alpha"}],
            emb.embed(["shared topic alpha"]),
        )
        store.upsert(
            [{"collection": COLLECTION_HISTORY, "content_sha": "h", "text": "shared topic alpha"}],
            emb.embed(["shared topic alpha"]),
        )
    finally:
        store.close()

    bg = rag.retrieve("shared topic alpha", collection=COLLECTION_BACKGROUND, k=5)
    hist = rag.retrieve("shared topic alpha", collection=COLLECTION_HISTORY, k=5)
    assert all(h.metadata["collection"] == COLLECTION_BACKGROUND for h in bg)
    assert all(h.metadata["collection"] == COLLECTION_HISTORY for h in hist)
    assert bg and hist


def test_index_items_is_idempotent_on_content_hash():
    rag.clear()
    items = [{
        "id": "d1", "source": "reddit", "url": "http://x/1",
        "title": "EAP610 firmware fails", "summary": "upgrade rollback",
        "impact_note": "check firmware", "subject": "omada_self",
        "category": "bug", "omada_impact": "needs_fix", "date": "2026-06-01",
    }]
    assert rag.index_items(items) == 1
    assert rag.index_items(items) == 1  # same content_hash -> replace, no dup
    assert rag.stats()["collections"].get(COLLECTION_HISTORY) == 1


def test_history_filter_by_subject():
    rag.clear()
    rag.index_items([
        {"id": "a", "source": "reddit", "url": "http://x/a", "title": "alpha self",
         "summary": "s", "subject": "omada_self", "category": "bug",
         "omada_impact": "needs_fix", "date": "2026-06-01"},
        {"id": "b", "source": "reddit", "url": "http://x/b", "title": "alpha comp",
         "summary": "s", "subject": "competitor", "category": "sentiment",
         "omada_impact": "threat", "date": "2026-06-01"},
    ])
    hits = rag.retrieve("alpha", collection=COLLECTION_HISTORY, k=5,
                        filters={"subject": "competitor"})
    assert hits and all(h.metadata["subject"] == "competitor" for h in hits)


def test_dim_guard_rebuilds_on_mismatch(tmp_path):
    p = tmp_path / "kb_dim.db"
    s1 = VectorStore(p, dim=8)
    s1.upsert([{"collection": "background", "content_sha": "x", "text": "t"}], [[0.0] * 8])
    assert s1.counts().get("background") == 1
    s1.close()

    s2 = VectorStore(p, dim=16)  # dimension changed -> disposable kb rebuilt
    assert s2.counts() == {}
    s2.close()
