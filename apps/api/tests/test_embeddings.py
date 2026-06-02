"""WS5: deterministic embedding seam (offline, no model download)."""

from __future__ import annotations

import math

from nintel.engine.embeddings import HashEmbedder, get_embedder


def test_hash_embedder_is_deterministic():
    e = HashEmbedder(dim=64)
    assert e.embed(["hello world"])[0] == e.embed(["hello world"])[0]


def test_hash_embedder_dim_and_normalized():
    v = HashEmbedder(dim=32).embed(["some 5g backup text"])[0]
    assert len(v) == 32
    assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-6


def test_hash_embedder_distinguishes_texts():
    e = HashEmbedder(dim=64)
    assert e.embed(["unifi 5g backup"])[0] != e.embed(["omada poe switch"])[0]


def test_get_embedder_selects_hash_from_env(settings):
    # conftest sets NINTEL_EMBEDDER=hash
    assert isinstance(get_embedder(), HashEmbedder)
