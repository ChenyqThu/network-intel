# CLAUDE.md — Network Intel (`nintel`)

Operational guide for AI sessions on this repo. Read this first.

## What this is
Internal competitive- & sentiment-intelligence engine for the TP-Link **Omada** network
team. Produces a **daily** report (舆情: Omada self + competitor) and a **weekly** report
(deep: + industry + store + dashboard), each rendered from one JSON contract. Live at
**`daily.omada.ink`**.

## ⛔ Overriding rule: NO FABRICATION
Every report sentence, source, and link must be **verifiably real**, drawn from
live-ingested items. Never invent URLs, products, metrics, or sources. The curator may
**cite only real items**; kos/RAG background is *reference-only* and must never become a
citation. (This rule exists because fabricated links shipped once and caused real damage.)

## Monorepo
- `apps/api/` — Python 3.11 · FastAPI · SQLAlchemy/SQLite · Pydantic v2 · Jinja2. Engine + REST + email.
- `apps/web/` — React 18 · Vite · TS. The "Dossier" reader (one stylesheet: `src/styles/dossier.css`).
- `contract/report.schema.json` — the engine↔frontend contract. The backend produces it; every frontend only renders it.

## The contract is law (right-extend only)
Backend may **only add optional fields** to `report.json`. Never: new required fields, a
`SectionKey` the frontend can't render, or cite-numbering breaks. Three files must stay in
sync: `contract/report.schema.json` (canonical) · `apps/api/src/nintel/contract.py`
(Pydantic, `extra="forbid"`) · `apps/web/src/types.ts` (TS mirror). **v1.4** added optional
`insights[]`, `sections[].insights`, and `funnel`.

## Pipeline — `apps/api/src/nintel/pipeline.py:build()`
`ingest → brand → select(初筛) → shortlist(Sonnet 精选) → classify(Haiku) → curate(Opus 策展) → trend → funnel → review gate → publish`

Three LLM tiers, each doing what it's best at: **Sonnet** judges *value* (which signals
matter), **Haiku** does cheap structured extraction, **Opus** synthesizes.

- **ingest** (`engine/ingest.py`) — connectors → normalized items → SQLite `intel_items` (dedup by `content_hash`). Skips `cadence="weekly"` connectors on a daily.
- **brand** (`engine/brand.py`) — LLM drops items merely *named* "Omada" (e.g. the Omada EV); omada_self candidates only.
- **select / 初筛** (`engine/select.py`) — Python rule-based coarse filter: **freshness window** (daily 2d / weekly 7d; provenance-`G` exempt), crosspost-collapse, turning-point re-surfacing, subject+source **balance**. Casts a **wide net** (`NINTEL_SELECT_PREFILTER_MAX`, default 80) — it no longer hard-caps to the final count, so it can't pre-judge away a valuable low-engagement item. Pure-Python and free.
- **shortlist / 精选** (`engine/shortlist.py` → `llm.shortlist_items`, **Sonnet**) — value-selects the ~80 down to `NINTEL_SHORTLIST_MAX` (default 15) via an editorial system prompt (`prompts/shortlist.md`: background / goal / filtering strategy). **Selects real items by index only** — never generates (NO-FABRICATION holds). Best-effort: any hiccup falls back to the prefilter order; offline returns the prefilter top-N. A Python safety-net guarantees omada_self is represented.
- **classify** (Haiku) — summary / category / signal_strength on the ~15 精选 items.
- **curate / 策展** (Opus, `engine/curate.py`) — **synthesis**: thematic `insights[]` (title + body + 💡takeaway + `cite_refs`) grouped by subject; the `lead`; the weekly `strategy`; subject-aware `omada_impact`. The **engine** (not the LLM) owns cite-id assignment, section assembly, citation-integrity asserts, prunes references to the cited set, and enum-guards LLM drift.
- **trend** (`engine/trend.py`) — `stats` + weekly `dashboard`.
- **funnel** — 采集(per source) → 初筛(select) → 精选(Sonnet) → 策展(cited) + byline → `report.funnel` (subtitle).

**LLM-optional.** Offline (`NINTEL_LLM_ENABLED` unset) replays the seed manifest
deterministically — that is how the test suite runs with no keys/network. Synthesis,
insights, funnel, and dynamic content only happen on the **live + LLM** path.

## Data sources (`NINTEL_LIVE_SOURCES`, `NINTEL_CONNECTOR_MODE=live`)
| | Source | Notes |
|---|---|---|
| A | omada-sentiment-monitor | Reddit / YouTube via **Notion** (canonical, hourly-synced); brand-aware subject |
| B | UNIFI_CHANNELS Supabase | releases / community / blog + `store_recent_*` (weekly store table) |
| C | industry RSS catalog | **weekly-only** (`cadence`); capped per feed (`NINTEL_RSS_MAX_PER_FEED`, default 8) |
| G | Gemini deep-research | **weekly-only**; grounded real sources; **freshness-exempt**; provenance `G` |
| D | strategy seed | seed-only |
| H | HTML scrape | **excluded** — not production-ready (per-site validation needed) |

## Curation model (v1.4 — synthesis, not per-item)
The report body is **section-grouped synthesized insights** that cite multiple real items
academically; the raw per-source items become the bottom **References** (and `全部条目`).
Three stores, two of them "raw":
1. **Firehose** — `intel_items` (~3000 rows): every ingested signal + dedup/heat state. State only; not in the UI.
2. **Extraction** — `report.items[]` (the cited subset, ~12): each source's summary/category/impact + URL. Shown in **全部条目**.
3. **Synthesis** — `report.insights[]`: cites items by `cite_id` (no duplication).

Daily sections = `omada_self` + `competitor`. Weekly adds `store` + `industry` + `dashboard`.

## kos / RAG (optional, `engine/rag.py` + `engine/gbrain.py`)
`NINTEL_RAG_ENABLED=true` + `NINTEL_KB_BACKEND=gbrain` injects **kos** Omada domain knowledge
into curate as `context.background` (reference-only, never citeable). `gbrain.py` is the kos
HTTP client (OAuth 2.1 client-credentials + MCP `search`). The `history` collection (past
reported items) stays local (sqlite-vec; embedder via `NINTEL_EMBEDDER` = `hash`|`fastembed`).
kos READ and WRITE (`put_page`) both work. Published reports auto-push to kos
(`NINTEL_KOS_PUBLISH=true`); the kos embed relay is flaky, so `index_report` retries
3× with backoff. Backfill a missed push: `python -m nintel.pipeline kb push-report --report-id <id>`.

## Admin review console — `apps/api/src/nintel/api/admin.py`, `apps/web/src/pages/AdminPage.tsx`
Route `/admin` (standalone; topbar has a 审核台 entry). Password = `NINTEL_ADMIN_PASSWORD`
(default `Lucien2026`), sent as the `X-Admin-Token` header. Review **pending** weeklies:
live preview (reuses `ReportView`), direct field/item edit, LLM conversational edit, publish/reject.

## Deploy — pm2 + Cloudflare tunnel (`ecosystem.config.cjs`)
- `nintel-api` :8000 (uvicorn) · `nintel-web` :5173 (vite **preview** of `dist/`) · `nintel-dev` :5174 (vite **HMR**, local-only).
- `daily.omada.ink` → :5173 (token tunnel, managed in the Cloudflare dashboard).
- The API reads the DB **fresh per request** → data fixes need **no redeploy**, just a browser refresh. **Frontend changes need `npm run build` + `pm2 restart nintel-web`.**
- crs = claude-relay-service: `ANTHROPIC_BASE_URL` (e.g. `http://127.0.0.1:8765/api`) + a `cr_` key drives the LLM calls.

## Commands
```bash
make test                                                 # api pytest + web vitest — run before claiming done
cd apps/web && npm run build                               # typecheck + bundle (run FROM apps/web, not repo root)
cd apps/api && .venv/bin/python scripts/regen_synth.py     # real regen (live + LLM + kos) → publish daily+weekly
pm2 restart nintel-api nintel-web                          # redeploy
```
Browser QA: use the gstack **`/browse`** skill (binary at `~/.claude/skills/gstack/browse/dist/browse`). Never `mcp__claude-in-chrome__*`.

## Gotchas
- **vite preview binds IPv6** — curl `localhost:5173`, not `127.0.0.1` (else `000`).
- **SQLAlchemy JSON column** — reassigning the same object reference doesn't mark it dirty; use a fresh object + `flag_modified(row, "payload")`.
- **Don't wipe `data/nintel.db`** (stateful: published reports + per-item dedup state). For a clean regen, build against a temp `NINTEL_DB_PATH` then publish to main — see `scripts/regen_synth.py`.
- **`get_settings()` is lru_cached** — call `get_settings.cache_clear()` after changing env in-process.
- **`.env` is gitignored + chmod 600** (real creds: crs, Supabase service-role JWT, `NOTION_TOKEN`, kos OAuth, Gemini). Never commit `.env` or `data/`.

## Key env vars
`NINTEL_CONNECTOR_MODE` · `NINTEL_LIVE_SOURCES` · `NINTEL_LLM_ENABLED` · `ANTHROPIC_API_KEY` /
`ANTHROPIC_BASE_URL` · `NINTEL_DAILY_WINDOW_DAYS` / `NINTEL_WEEKLY_WINDOW_DAYS` ·
`NINTEL_SELECT_PREFILTER_MAX` (初筛 80) · `NINTEL_SHORTLIST_MAX` (精选 15) ·
`NINTEL_SONNET_MODEL` · `NINTEL_RSS_MAX_PER_FEED` · `NINTEL_RAG_ENABLED` ·
`NINTEL_KB_BACKEND` · `NINTEL_EMBEDDER` · `NINTEL_ADMIN_PASSWORD` · `NINTEL_REPORT_BYLINE` ·
`KOS_MCP_BASE` / `KOS_OAUTH_*` · `SUPABASE_URL` / `SUPABASE_KEY` · `NOTION_TOKEN` · `GEMINI_API_KEY`.
