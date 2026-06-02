"""Shared pytest fixtures.

Every test runs fully offline: ``NINTEL_LLM_ENABLED`` is forced off and the DB
is pointed at a per-session tmp file so tests never touch the dev database or
the network.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _offline_env(tmp_path_factory: pytest.TempPathFactory):
    """Force offline mode + an isolated DB/data dir for the whole session."""

    data_dir: Path = tmp_path_factory.mktemp("nintel-data")
    os.environ["NINTEL_LLM_ENABLED"] = "false"
    os.environ["NINTEL_CONNECTOR_MODE"] = "fixture"
    os.environ["NINTEL_REVIEW_MODE"] = "manual"
    os.environ["NINTEL_DATA_DIR"] = str(data_dir)
    os.environ["NINTEL_DB_PATH"] = str(data_dir / "test.db")
    # RAG stays off by default; when a test enables it, use the deterministic
    # hash embedder + an isolated kb.db so the vector path runs with no model
    # download and no network.
    os.environ["NINTEL_RAG_ENABLED"] = "false"
    os.environ["NINTEL_EMBEDDER"] = "hash"
    os.environ["NINTEL_KB_DB_PATH"] = str(data_dir / "kb.db")
    os.environ["NINTEL_KB_BACKEND"] = "local"
    # Hermetic tests: neutralize anything a local apps/api/.env (real creds,
    # crs/kos endpoints, live sources) would inject via python-dotenv.
    for _leak in (
        "SUPABASE_URL", "SUPABASE_KEY", "NOTION_TOKEN", "NOTION_DATABASE_ID",
        "NOTION_YOUTUBE_DATABASE_ID", "KOS_MCP_BASE", "KOS_OAUTH_CLIENT_ID",
        "KOS_OAUTH_CLIENT_SECRET", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
        "NINTEL_LIVE_SOURCES", "NINTEL_PROMPT_DIR", "NINTEL_KOS_PUBLISH",
        "NINTEL_KOS_SLUG_PREFIX",
    ):
        os.environ.pop(_leak, None)

    # Reset the cached settings so the env overrides take effect.
    from nintel.config import get_settings

    get_settings.cache_clear()
    yield


@pytest.fixture()
def settings():
    from nintel.config import get_settings

    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(scope="session")
def contract_dir() -> Path:
    from nintel.config import get_settings

    return get_settings().contract_dir
