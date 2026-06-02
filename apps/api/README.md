# Network Intel — Backend (`apps/api`)

The **engine + REST API** for Network Intel (`nintel`): an internal competitive &
sentiment intelligence station for the TP-Link network products team. The whole
system is wired around a single contract — `report.json`
(`contract/report.schema.json`, PRD v1.3 §7.9). The engine **produces** it; every
frontend (web / email / Feishu) only **renders** it.

- Python 3.11 · FastAPI · Uvicorn · SQLAlchemy 2.x + SQLite · Pydantic v2 ·
  Jinja2 · pytest · jsonschema · python-dotenv
- Anthropic SDK is **optional** (LLM stage gated behind `NINTEL_LLM_ENABLED`,
  default off). The whole system — and the entire test-suite — runs **offline**
  with no API key.

## Architecture

```
src/nintel/
├── contract.py          Pydantic v2 models == report.schema.json + jsonschema bridge
├── config.py            env-driven Settings (.env via python-dotenv)
├── pipeline.py          orchestrates ingest→classify→curate→trend→render + CLI
├── connectors/          Connector protocol + fixture-backed readers
│   ├── base.py            RawRow, Connector, mode guard, seed-row builder
│   ├── supabase.py        Source B — UNIFI_CHANNELS (releases/blog/community/store)
│   ├── sentiment_monitor.py  Source A — Notion Reddit/YouTube (+ sentiment/relevance/switch_intent)
│   └── rss.py             Source C — industry RSS
├── engine/
│   ├── ingest.py          raw rows → IntelItem → SQLite, dedupe by content_hash (sha256)
│   ├── classify.py        Haiku stage: summary/category/signal_strength (fixture fallback)
│   ├── curate.py          Opus stage: sections, subject-aware omada_impact, lead, strategy, cite_id, references
│   ├── trend.py           weekly analytics: by_source/by_impact/top_hot + dashboard
│   ├── render.py          Jinja2 → email HTML (daily/weekly) + Markdown (Feishu)
│   └── llm.py             optional Anthropic stage (Haiku+Opus, prompt caching) — gated
├── store/               SQLAlchemy models (intel_items, reports), session, init_db(), seed()
├── review/              human-review gate: data/pending → approve() → data/published
└── api/                 FastAPI app + read-side repository
prompts/                 统一提示词 (classify.md, curate_daily.md, curate_weekly.md)
templates/               daily_email.html.j2, weekly_email.html.j2, _macros.html.j2
tests/                   pytest (offline)
```

### Subject-aware impact semantics (PRD §2.1)
- `subject = omada_self` → `needs_fix` | `feature_input` | `strength_confirm`
- `subject = competitor` → `threat` | `opportunity` | `neutral`
- `subject = industry`   → `opportunity` | `neutral`

### Connectors
The real upstreams (UNIFI_CHANNELS Supabase, omada-sentiment-monitor Notion) and
their credentials are **not present** in this environment, so the readers are
**fixture-backed** — they reconstruct raw rows from the canonical seed reports
(split by `provenance`/`source`). Each exposes the exact signature a live reader
would (`fetch(since: date) -> list[RawRow]`), so a live Supabase/Notion/RSS
client is a drop-in. Switch via `NINTEL_CONNECTOR_MODE=fixture|live` (default
`fixture`; `live` raises `NotImplementedError` with a clear message).

### LLM stage (optional, off by default)
`engine/llm.py` uses the Anthropic SDK with **prompt caching** (the shared
instruction block in `prompts/` is the cached system prefix; per-item/per-report
data goes in the user turn). Models: Haiku `claude-haiku-4-5-20251001` (classify),
Opus `claude-opus-4-8` (curate, adaptive thinking + high effort). Gated behind
`NINTEL_LLM_ENABLED=false` (default) — when disabled the pipeline uses the
deterministic fixture path and never touches the network.

## Setup

```bash
cd apps/api
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt      # runtime + test deps
.venv/bin/pip install -e .                      # install the `nintel` package
# optional LLM stage:  .venv/bin/pip install -e .[llm]
cp .env.example .env                            # optional; defaults run offline
```

## Initialize the database & seed the contract

```bash
.venv/bin/python -m nintel.pipeline seed --reset
# -> seeded: 2 reports, 21 items   (data/nintel.db, gitignored)
```

## Build reports (CLI)

```bash
.venv/bin/python -m nintel.pipeline build --type daily            # → data/pending/ (manual review)
.venv/bin/python -m nintel.pipeline build --type weekly --publish # → data/published/ (skip review)
.venv/bin/python -m nintel.pipeline approve 2026-06-01-daily      # pending → published
.venv/bin/python -m nintel.pipeline render --type weekly          # email HTML → stdout
```

Built reports are schema-valid and content-equivalent to the canonical seeds.

## Run the API

```bash
.venv/bin/python -m uvicorn nintel.api.app:app --host 127.0.0.1 --port 8000
# health check:
curl http://127.0.0.1:8000/api/health
curl "http://127.0.0.1:8000/api/reports/latest?type=weekly"
```

Base URL `http://localhost:8000`, prefix `/api`. CORS allows `http://localhost:5173`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | `{status, version}` |
| GET | `/api/reports` | archive index (from `archive.json`/DB) |
| GET | `/api/archive` | alias of `/api/reports` |
| GET | `/api/reports/latest?type=daily\|weekly` | newest full report of the type |
| GET | `/api/reports/{report_id}` | full report (contract JSON); 404 (clear message) for metadata-only archive entries |
| GET | `/api/reports/{report_id}/email` | rendered email HTML (`text/html`) |
| GET | `/api/items` | flat item stream; filters: `subject`, `source`, `impact`, `type`, `tier`, `q` |

The two full seed reports (`2026-06-01-daily`, `2026-W22-weekly`) are served
fully; the other `archive.json` entries are metadata-only and return an honest
404 for their full report.

## Tests

```bash
.venv/bin/python -m pytest -q        # all green, fully offline
```

Covers: contract round-trip (lossless + schema-valid) and a negative schema test;
pipeline builds (section keys, subject-aware impacts, cite_id↔reference integrity,
resolvable `{{cite:N}}`); FastAPI endpoints + `/api/items` filters + `/email`;
email/markdown render (omada_self section, new impact labels, references,
strategy/store/dashboard); connectors (mode switch, dedupe) and the review gate.

## Configuration (env)

| Var | Default | Meaning |
|-----|---------|---------|
| `NINTEL_PORT` | `8000` | HTTP port |
| `NINTEL_CORS_ORIGINS` | `http://localhost:5173,…` | CORS allow-list |
| `NINTEL_DB_PATH` | `./data/nintel.db` | SQLite file (gitignored) |
| `NINTEL_CONNECTOR_MODE` | `fixture` | `fixture` \| `live` |
| `NINTEL_REVIEW_MODE` | `manual` | `manual` (pending) \| `auto` (publish) |
| `NINTEL_LLM_ENABLED` | `false` | enable the Anthropic classify/curate stages |
| `ANTHROPIC_API_KEY` | — | required only when LLM is enabled |

No secrets are committed; `.venv`, `__pycache__`, `*.db`, and the review queues
are gitignored (`data/pending` / `data/published` keep a `.gitkeep`).
