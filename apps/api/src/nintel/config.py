"""Environment-driven settings for the nintel backend.

All knobs are read from the process environment (optionally loaded from a
``.env`` file via ``python-dotenv``). Nothing here requires network access or
secrets to start — the defaults run the system fully offline against the seed
fixtures, which is exactly what the test-suite and a fresh checkout rely on.

Key flags
---------
``NINTEL_CONNECTOR_MODE``  ``fixture`` (default) | ``live``
    ``live`` readers raise ``NotImplementedError`` here (no upstream creds).
``NINTEL_LLM_ENABLED``     ``false`` (default) | ``true``
    When false the classify/curate stages use the deterministic fixture path
    and never touch the network.
``NINTEL_REVIEW_MODE``     ``manual`` (default) | ``auto``
    ``manual`` writes report.json to ``data/pending/`` awaiting human approval;
    ``auto`` publishes straight to ``data/published/``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

try:  # python-dotenv is a hard dependency, but stay import-safe.
    from dotenv import dotenv_values, find_dotenv, load_dotenv

    _envfile = find_dotenv()
    # override=False: the real environment (shell / launchd / cron) wins over
    # .env, so runtime + per-job config works. BUT the host (e.g. a Claude Code
    # harness) injects ANTHROPIC_BASE_URL + an empty ANTHROPIC_API_KEY that would
    # mask the project's values — so force just those two from .env.
    load_dotenv(_envfile, override=False)
    if _envfile:
        _vals = dotenv_values(_envfile)
        for _k in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY"):
            if _vals.get(_k):
                os.environ[_k] = _vals[_k]
except Exception:  # pragma: no cover - defensive only
    pass


# ---------------------------------------------------------------------------
# Filesystem anchors
# ---------------------------------------------------------------------------
# src/nintel/config.py -> src/nintel -> src -> apps/api
API_ROOT = Path(__file__).resolve().parents[2]
# apps/api -> apps -> repo root
REPO_ROOT = API_ROOT.parents[1]
CONTRACT_DIR = REPO_ROOT / "contract"
SCHEMA_PATH = CONTRACT_DIR / "report.schema.json"
PROMPTS_DIR = API_ROOT / "prompts"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable, env-resolved settings snapshot."""

    # HTTP server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    # Storage
    data_dir: Path = API_ROOT / "data"
    db_path: Path = API_ROOT / "data" / "nintel.db"

    # Pipeline behaviour
    connector_mode: str = "fixture"  # fixture | live
    # Subset of source provenances {A,B,C} that run live when connector_mode=live.
    # Default empty -> live mode raises for every source (preserves the loud
    # "not provisioned" behaviour); add sources here to enable them one at a time.
    live_sources: frozenset[str] = frozenset()
    # Source A (sentiment) reads the omada-sentiment-monitor SQLite directly (DB,
    # not Notion). Absolute path to omada_monitor.db.
    sentiment_db_path: str | None = None
    llm_enabled: bool = False
    review_mode: str = "manual"  # manual | auto

    # Selection / cross-day re-surface thresholds (WS1). Defaults are chosen so
    # the offline path is unaffected (it never runs selection into curate).
    resurface_heat_delta: int = 50      # absolute heat jump that counts as a spike
    resurface_heat_ratio: float = 2.0   # OR heat >= ratio * previous heat
    resurface_cooldown_days: int = 3    # min days since last_reported before re-surface
    select_min_heat: int = 0            # noise floor for a NEW item to qualify
    select_max_items_daily: int = 12    # cap the selected pool
    # Freshness window: an item only qualifies for a report if its publish date
    # is within this many days of the report's as_of date (and not in the
    # future). Without this, "never reported" was treated as "new", so months-
    # old items leaked into a daily. daily=2 covers as_of + the prior day;
    # weekly=7 covers the as_of ISO week (Mon..Sun when as_of is the Sunday).
    daily_window_days: int = 2
    weekly_window_days: int = 7

    # RAG / vector knowledge base (WS5). Off by default; kb_enabled() also
    # requires llm_enabled (retrieved text only matters if the LLM consumes it).
    rag_enabled: bool = False
    rag_classify: bool = False          # also inject background at classify tier
    embedder: str = "fastembed"         # fastembed | hash
    hash_embedder_dim: int = 64
    kb_db_path: Path = API_ROOT / "data" / "kb.db"
    fastembed_cache: str | None = None
    knowledge_dir: Path = API_ROOT / "knowledge"
    # Background-knowledge retrieval backend: local sqlite-vec corpus, or the
    # kos/gbrain HTTP service. (history retrieval is always local.)
    kb_backend: str = "local"  # local | gbrain
    kos_mcp_base: str | None = None
    kos_oauth_client_id: str | None = None
    kos_oauth_client_secret: str | None = None
    # Push published reports into kos (put_page under the client's write source).
    kos_publish: bool = False
    kos_slug_prefix: str = "network-intel"

    # LLM (only used when llm_enabled)
    anthropic_api_key: str | None = None
    # Custom Anthropic-compatible endpoint (e.g. a claude-relay-service / crs
    # gateway). When set, the SDK is pointed here instead of api.anthropic.com.
    anthropic_base_url: str | None = None
    haiku_model: str = "claude-haiku-4-5-20251001"
    opus_model: str = "claude-opus-4-8"

    # Contract
    contract_dir: Path = CONTRACT_DIR
    schema_path: Path = SCHEMA_PATH
    prompts_dir: Path = PROMPTS_DIR

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    @property
    def pending_dir(self) -> Path:
        return self.data_dir / "pending"

    @property
    def published_dir(self) -> Path:
        return self.data_dir / "published"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build a cached :class:`Settings` from the current environment."""

    data_dir = Path(os.getenv("NINTEL_DATA_DIR", str(API_ROOT / "data"))).resolve()
    db_path = Path(os.getenv("NINTEL_DB_PATH", str(data_dir / "nintel.db"))).resolve()

    cors_raw = os.getenv("NINTEL_CORS_ORIGINS")
    cors = (
        tuple(o.strip() for o in cors_raw.split(",") if o.strip())
        if cors_raw
        else ("http://localhost:5173", "http://127.0.0.1:5173")
    )

    return Settings(
        host=os.getenv("NINTEL_HOST", "0.0.0.0"),
        port=int(os.getenv("NINTEL_PORT", "8000")),
        cors_origins=cors,
        data_dir=data_dir,
        db_path=db_path,
        connector_mode=os.getenv("NINTEL_CONNECTOR_MODE", "fixture").strip().lower(),
        live_sources=frozenset(
            s.strip().upper()
            for s in os.getenv("NINTEL_LIVE_SOURCES", "").split(",")
            if s.strip()
        ),
        sentiment_db_path=os.getenv("NINTEL_SENTIMENT_DB_PATH") or None,
        llm_enabled=_env_bool("NINTEL_LLM_ENABLED", False),
        review_mode=os.getenv("NINTEL_REVIEW_MODE", "manual").strip().lower(),
        resurface_heat_delta=int(os.getenv("NINTEL_RESURFACE_HEAT_DELTA", "50")),
        resurface_heat_ratio=float(os.getenv("NINTEL_RESURFACE_HEAT_RATIO", "2.0")),
        resurface_cooldown_days=int(os.getenv("NINTEL_RESURFACE_COOLDOWN_DAYS", "3")),
        select_min_heat=int(os.getenv("NINTEL_SELECT_MIN_HEAT", "0")),
        select_max_items_daily=int(os.getenv("NINTEL_SELECT_MAX_ITEMS_DAILY", "12")),
        daily_window_days=int(os.getenv("NINTEL_DAILY_WINDOW_DAYS", "2")),
        weekly_window_days=int(os.getenv("NINTEL_WEEKLY_WINDOW_DAYS", "7")),
        rag_enabled=_env_bool("NINTEL_RAG_ENABLED", False),
        rag_classify=_env_bool("NINTEL_RAG_CLASSIFY", False),
        embedder=os.getenv("NINTEL_EMBEDDER", "fastembed").strip().lower(),
        hash_embedder_dim=int(os.getenv("NINTEL_HASH_EMBEDDER_DIM", "64")),
        kb_db_path=Path(os.getenv("NINTEL_KB_DB_PATH", str(data_dir / "kb.db"))).resolve(),
        fastembed_cache=os.getenv("NINTEL_FASTEMBED_CACHE"),
        knowledge_dir=Path(
            os.getenv("NINTEL_KNOWLEDGE_DIR", str(API_ROOT / "knowledge"))
        ).resolve(),
        kb_backend=os.getenv("NINTEL_KB_BACKEND", "local").strip().lower(),
        kos_mcp_base=os.getenv("KOS_MCP_BASE") or None,
        kos_oauth_client_id=os.getenv("KOS_OAUTH_CLIENT_ID") or None,
        kos_oauth_client_secret=os.getenv("KOS_OAUTH_CLIENT_SECRET") or None,
        kos_publish=_env_bool("NINTEL_KOS_PUBLISH", False),
        kos_slug_prefix=os.getenv("NINTEL_KOS_SLUG_PREFIX", "network-intel"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL") or None,
        haiku_model=os.getenv("NINTEL_HAIKU_MODEL", "claude-haiku-4-5-20251001"),
        opus_model=os.getenv("NINTEL_OPUS_MODEL", "claude-opus-4-8"),
        # Override to A/B a candidate prompt set (e.g. prompts/variants/).
        prompts_dir=Path(os.getenv("NINTEL_PROMPT_DIR", str(PROMPTS_DIR))).resolve(),
    )
