"""RAG vector knowledge base over sqlite-vec (engine/rag.py).

Two collections in a standalone ``data/kb.db`` (kept separate from the ORM DB so
the loadable extension never touches the FastAPI connection):

* ``background`` — curated markdown corpus (``knowledge/*.md``): competitor
  specs, glossary, positioning.
* ``history`` — past *reported* items (title + summary + impact_note), so the
  curator can see what's already been covered and judge turning points.

Off by default: :func:`kb_enabled` requires ``NINTEL_RAG_ENABLED`` *and*
``llm_enabled``. Embeddings come from :mod:`nintel.engine.embeddings`, so tests
run fully offline with the deterministic ``HashEmbedder``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import get_settings
from .embeddings import get_embedder

COLLECTION_BACKGROUND = "background"
COLLECTION_HISTORY = "history"


def kb_enabled() -> bool:
    s = get_settings()
    return bool(s.rag_enabled and s.llm_enabled)


@dataclass
class Hit:
    text: str
    score: float
    metadata: dict[str, Any]


# --------------------------------------------------------------------------- #
# Vector store
# --------------------------------------------------------------------------- #
class VectorStore:
    """Thin wrapper over a sqlite-vec-backed kb.db."""

    def __init__(self, db_path: Path, dim: int) -> None:
        import sqlite3

        self.dim = dim
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(self._conn)
        self._conn.enable_load_extension(False)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        c = self._conn
        c.execute("CREATE TABLE IF NOT EXISTS kb_meta (k TEXT PRIMARY KEY, v TEXT)")
        row = c.execute("SELECT v FROM kb_meta WHERE k='dim'").fetchone()
        if row is not None and int(row[0]) != self.dim:
            # Embedding dimension changed -> kb.db is disposable, rebuild it.
            c.execute("DROP TABLE IF EXISTS kb_chunks")
            c.execute("DROP TABLE IF EXISTS kb_vec")
            c.execute("DELETE FROM kb_meta")
            row = None
        c.execute(
            """CREATE TABLE IF NOT EXISTS kb_chunks (
                rowid INTEGER PRIMARY KEY,
                collection TEXT, doc_id TEXT, item_id TEXT, report_id TEXT,
                subject TEXT, source TEXT, category TEXT, omada_impact TEXT,
                url TEXT, date TEXT, heading TEXT, content_sha TEXT, text TEXT)"""
        )
        c.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS kb_vec USING vec0(embedding float[{self.dim}])"
        )
        if row is None:
            c.execute("INSERT OR REPLACE INTO kb_meta(k,v) VALUES ('dim', ?)", (str(self.dim),))
        c.commit()

    def upsert(self, rows: list[dict], embeddings: list[list[float]]) -> int:
        import sqlite_vec

        c = self._conn
        n = 0
        for meta, emb in zip(rows, embeddings):
            old = c.execute(
                "SELECT rowid FROM kb_chunks WHERE collection=? AND content_sha=?",
                (meta["collection"], meta["content_sha"]),
            ).fetchone()
            if old is not None:  # idempotent: replace existing chunk
                c.execute("DELETE FROM kb_vec WHERE rowid=?", (old[0],))
                c.execute("DELETE FROM kb_chunks WHERE rowid=?", (old[0],))
            cur = c.execute(
                """INSERT INTO kb_chunks
                   (collection,doc_id,item_id,report_id,subject,source,category,
                    omada_impact,url,date,heading,content_sha,text)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    meta.get("collection"), meta.get("doc_id"), meta.get("item_id"),
                    meta.get("report_id"), meta.get("subject"), meta.get("source"),
                    meta.get("category"), meta.get("omada_impact"), meta.get("url"),
                    meta.get("date"), meta.get("heading"), meta.get("content_sha"),
                    meta.get("text"),
                ),
            )
            c.execute(
                "INSERT INTO kb_vec(rowid, embedding) VALUES (?, ?)",
                (cur.lastrowid, sqlite_vec.serialize_float32(list(emb))),
            )
            n += 1
        c.commit()
        return n

    def query(
        self,
        embedding: list[float],
        *,
        collection: str | None,
        k: int,
        filters: dict | None = None,
        min_score: float = 0.0,
    ) -> list[Hit]:
        import sqlite_vec

        # Two-step KNN: nearest rowids from the vec table, then metadata + filter.
        knn = self._conn.execute(
            "SELECT rowid, distance FROM kb_vec WHERE embedding MATCH ? "
            "ORDER BY distance LIMIT ?",
            (sqlite_vec.serialize_float32(list(embedding)), max(k * 5, k)),
        ).fetchall()
        hits: list[Hit] = []
        for rid, dist in knn:
            row = self._conn.execute(
                "SELECT text,collection,doc_id,item_id,report_id,subject,source,"
                "category,omada_impact,url,date,heading FROM kb_chunks WHERE rowid=?",
                (rid,),
            ).fetchone()
            if row is None:
                continue
            meta = {
                "collection": row[1], "doc_id": row[2], "item_id": row[3],
                "report_id": row[4], "subject": row[5], "source": row[6],
                "category": row[7], "omada_impact": row[8], "url": row[9],
                "date": row[10], "heading": row[11],
            }
            if collection and meta["collection"] != collection:
                continue
            if filters and any(meta.get(fk) != fv for fk, fv in filters.items()):
                continue
            score = 1.0 / (1.0 + float(dist))  # L2 distance -> (0,1] similarity
            if score < min_score:
                continue
            hits.append(Hit(text=row[0], score=score, metadata=meta))
            if len(hits) >= k:
                break
        return hits

    def counts(self) -> dict[str, int]:
        return {
            r[0]: r[1]
            for r in self._conn.execute(
                "SELECT collection, COUNT(*) FROM kb_chunks GROUP BY collection"
            ).fetchall()
        }

    def clear(self, collection: str | None = None) -> None:
        c = self._conn
        if collection:
            for (rid,) in c.execute(
                "SELECT rowid FROM kb_chunks WHERE collection=?", (collection,)
            ).fetchall():
                c.execute("DELETE FROM kb_vec WHERE rowid=?", (rid,))
            c.execute("DELETE FROM kb_chunks WHERE collection=?", (collection,))
        else:
            c.execute("DELETE FROM kb_vec")
            c.execute("DELETE FROM kb_chunks")
        c.commit()

    def close(self) -> None:
        self._conn.close()


def get_store() -> VectorStore:
    return VectorStore(Path(get_settings().kb_db_path), get_embedder().dim)


# --------------------------------------------------------------------------- #
# Chunking + ingestion
# --------------------------------------------------------------------------- #
def _chunk_markdown(md: str, *, max_chars: int = 1500) -> list[tuple[str, str]]:
    """Header-aware split: (heading, body) pairs, overlong bodies sub-split."""
    heading = ""
    buf: list[str] = []
    sections: list[tuple[str, str]] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            sections.append((heading, body))

    for line in md.splitlines():
        if line.lstrip().startswith("#"):
            flush()
            buf = []
            heading = line.lstrip("#").strip()
        else:
            buf.append(line)
    flush()

    out: list[tuple[str, str]] = []
    for h, body in sections:
        if len(body) <= max_chars:
            out.append((h, body))
        else:
            for i in range(0, len(body), max_chars):
                out.append((h, body[i : i + max_chars]))
    return out


def reindex_background() -> dict[str, int]:
    """(Re)chunk + embed ``knowledge/*.md`` into the background collection."""
    kdir = Path(get_settings().knowledge_dir)
    store = get_store()
    emb = get_embedder()
    try:
        store.clear(COLLECTION_BACKGROUND)
        rows: list[dict] = []
        texts: list[str] = []
        for md_path in sorted(kdir.glob("**/*.md")):
            doc_id = str(md_path.relative_to(kdir))
            for ix, (heading, body) in enumerate(
                _chunk_markdown(md_path.read_text(encoding="utf-8"))
            ):
                text = f"{heading}\n{body}" if heading else body
                sha = hashlib.sha256(
                    f"background|{doc_id}|{heading}|{ix}|{text}".encode("utf-8")
                ).hexdigest()
                rows.append(
                    {
                        "collection": COLLECTION_BACKGROUND,
                        "doc_id": doc_id,
                        "heading": heading,
                        "content_sha": sha,
                        "text": text,
                    }
                )
                texts.append(text)
        added = store.upsert(rows, emb.embed(texts)) if texts else 0
    finally:
        store.close()
    return {"collection": 1, "added": added}


def index_items(items: list[dict]) -> int:
    """Index published report items into the history collection (idempotent)."""
    from .ingest import content_hash

    items = [it for it in (items or []) if it.get("url")]
    if not items:
        return 0
    store = get_store()
    emb = get_embedder()
    try:
        rows: list[dict] = []
        texts: list[str] = []
        for it in items:
            text = "\n".join(
                p for p in (it.get("title"), it.get("summary"), it.get("impact_note")) if p
            )
            sha = content_hash(it["source"], it["url"], it["title"])
            rows.append(
                {
                    "collection": COLLECTION_HISTORY,
                    "item_id": it.get("id"),
                    "url": it.get("url"),
                    "date": it.get("date"),
                    "subject": it.get("subject"),
                    "source": it.get("source"),
                    "category": it.get("category"),
                    "omada_impact": it.get("omada_impact"),
                    "content_sha": sha,
                    "text": text,
                }
            )
            texts.append(text)
        return store.upsert(rows, emb.embed(texts))
    finally:
        store.close()


# --------------------------------------------------------------------------- #
# Retrieval + formatting
# --------------------------------------------------------------------------- #
def retrieve(
    query_text: str,
    *,
    collection: str,
    k: int = 4,
    filters: dict | None = None,
    min_score: float = 0.0,
) -> list[Hit]:
    emb = get_embedder().embed([query_text])[0]
    store = get_store()
    try:
        return store.query(
            emb, collection=collection, k=k, filters=filters, min_score=min_score
        )
    finally:
        store.close()


def format_context(hits: list[Hit], *, budget_chars: int = 4000) -> str:
    """Join hit texts under a char budget (~4 chars/token), best-scoring first."""
    out: list[str] = []
    used = 0
    for h in hits:
        chunk = (h.text or "").strip()
        if not chunk:
            continue
        if used + len(chunk) > budget_chars:
            chunk = chunk[: max(0, budget_chars - used)]
        if not chunk:
            break
        out.append(chunk)
        used += len(chunk)
    return "\n---\n".join(out)


def summarize_hits(hits: list[Hit]) -> list[dict[str, Any]]:
    """Compact prior-coverage rows for the curate prompt (no full text)."""
    rows = []
    for h in hits:
        title = (h.text or "").splitlines()[0] if h.text else (h.metadata.get("item_id") or "")
        rows.append(
            {
                "title": title,
                "date": h.metadata.get("date"),
                "impact": h.metadata.get("omada_impact"),
                "url": h.metadata.get("url"),
            }
        )
    return rows


def stats() -> dict[str, Any]:
    store = get_store()
    try:
        return {"dim": store.dim, "collections": store.counts()}
    finally:
        store.close()


def clear(collection: str | None = None) -> None:
    store = get_store()
    try:
        store.clear(collection)
    finally:
        store.close()
