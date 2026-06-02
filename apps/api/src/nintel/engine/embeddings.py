"""Pluggable text embeddings for the RAG layer.

Two backends behind one protocol, selected by ``NINTEL_EMBEDDER``:

* ``HashEmbedder`` (``hash``) — deterministic, stdlib-only pseudo-embeddings.
  No model, no network, same text -> same vector. Tests use this so the whole
  vector pipeline (chunk -> embed -> upsert -> KNN) runs offline + reproducibly.
* ``FastEmbedEmbedder`` (``fastembed``, default) — real local ONNX embeddings
  (BAAI/bge-small-en-v1.5, 384-dim). Imported lazily so the optional dependency
  is only needed when actually selected.
"""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Protocol, runtime_checkable

from ..config import get_settings


@runtime_checkable
class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class HashEmbedder:
    """Deterministic hash embedding (no deps, offline) for tests/dev.

    Each whitespace token is expanded into ``dim`` pseudo-random components via
    SHA-256, summed, then L2-normalized. Reproducible, but NOT production
    retrieval quality — use fastembed for that.
    """

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = (text or "").lower().split() or [""]
        for tok in tokens:
            seed = tok.encode("utf-8")
            buf = b""
            i = 0
            while len(buf) < self.dim * 4:  # 4 bytes per dimension
                buf += hashlib.sha256(seed + struct.pack(">I", i)).digest()
                i += 1
            for d in range(self.dim):
                val = int.from_bytes(buf[d * 4 : d * 4 + 4], "big") / 0xFFFFFFFF
                vec[d] += val - 0.5
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


class FastEmbedEmbedder:
    """Local ONNX embeddings via fastembed (optional ``[rag]`` dependency)."""

    dim = 384

    def __init__(
        self, model: str = "BAAI/bge-small-en-v1.5", cache_dir: str | None = None
    ) -> None:
        from fastembed import TextEmbedding  # lazy: only when selected

        self._model = TextEmbedding(model_name=model, cache_dir=cache_dir)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._model.embed(list(texts))]


def get_embedder() -> Embedder:
    s = get_settings()
    if (s.embedder or "fastembed").lower() == "hash":
        return HashEmbedder(dim=s.hash_embedder_dim)
    return FastEmbedEmbedder(cache_dir=s.fastembed_cache)
