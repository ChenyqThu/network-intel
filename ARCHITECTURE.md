# Network Intel (`nintel`) — Architecture

Full-stack implementation of the **Network Intel** internal competitive-intelligence station
for the TP-Link **Omada** network team. Origin spec: `docs/PRD.md` + `docs/SOLUTION.md` +
`docs/SAMPLE_REPORT.md` + the **Dossier** design system (`docs/DESIGN_HANDOFF_v2/v3`).
Operational conventions for AI sessions live in **`CLAUDE.md`**; ADRs in `docs/DECISIONS.md`.

---

## 1. What we are building

An internal-only competitive & sentiment intelligence reader. Two cadences:

- **Daily** (舆情): `Omada self-sentiment → Competitor`.
- **Weekly** (deep): `🎯 Market-Strategy Insight (pinned) → Omada self → Competitor → Store moves
  → Industry → Analytics dashboard`.

The product's soul is **one-click traceability + no fabrication**: every conclusion is a
**synthesis of real, link-verified signals**, cited academically and resolvable to a numbered
References list. Nothing is invented — see the NO-FABRICATION rule in `CLAUDE.md`.

The system is wired around **one contract**, `report.json`. The engine produces it; every
frontend (web / email) only renders it. Canonical schema: `contract/report.schema.json`.

## 2. Tech stack

| Layer | Choice | Notes |
|-------|--------|-------|
| **Contract** | `report.json` + JSON Schema | Single engine↔frontend contract; right-extend only. Mirrored by `contract.py` (Pydantic) + `types.ts`. |
| **Backend** | Python 3.11 · FastAPI · SQLite (SQLAlchemy, WAL) · Pydantic v2 | Engine stages + REST + Jinja2 email. Pydantic models *are* the schema, validated at the boundary. |
| **LLM (3-tier)** | Anthropic SDK — **Sonnet** (shortlist/精选) + **Haiku** (classify) + **Opus** (curate), prompt caching | Routed through a **claude-relay-service** (`ANTHROPIC_BASE_URL` + `cr_` key). Gated by `NINTEL_LLM_ENABLED`; offline replays the seed manifest deterministically. |
| **Connectors** | Live readers behind a `Connector` protocol | A=sentiment(Notion) · B=Supabase · C=RSS · G=Gemini. `NINTEL_CONNECTOR_MODE=live` + `NINTEL_LIVE_SOURCES`; fixture fallback for offline/tests. |
| **RAG / kos** | sqlite-vec (`history`) + kos HTTP (`background`) | Optional Omada domain knowledge fed to the curator as reference-only context. |
| **Frontend** | React 18 · Vite · TypeScript | Pixel-faithful Dossier port; one stylesheet `src/styles/dossier.css`. |
| **Deploy** | pm2 + Cloudflare tunnel | `daily.omada.ink` → vite preview :5173 → proxies `/api` → :8000. |

### Repository layout
```
contract/   report.schema.json · seed daily/weekly · archive.json   ← source of truth
apps/api/   src/nintel/{connectors,engine,store,review,api,templates}
            prompts/ · knowledge/ (RAG corpus) · scripts/ (regen) · tests/
apps/web/   src/{components,pages,lib,api,styles,fixtures,test}
docs/       CONTRACT · DECISIONS · PRD · SOLUTION · SAMPLE_REPORT · design handoffs
project/    original Claude Design handoff (prototype) — reference
ecosystem.config.cjs   pm2 process defs (api / web / dev)
CLAUDE.md   operational guide for AI sessions
```

## 3. The pipeline (`apps/api/src/nintel/pipeline.py:build()`)

```
ingest → brand → select(初筛) → shortlist(Sonnet 精选) → classify(Haiku) → curate(Opus 策展) → trend → funnel → gate → publish
```

Three LLM tiers, each doing what it's best at: **Sonnet** judges value (which signals matter),
**Haiku** does cheap structured extraction, **Opus** synthesizes.

1. **ingest** (`engine/ingest.py`) — every connector → normalized item dicts → persisted to
   SQLite `intel_items` (dedup by `content_hash(source,url,title)`). On a daily, connectors
   declaring `cadence="weekly"` (C, G) are skipped.
2. **brand** (`engine/brand.py`) — LLM brand-disambiguation: drops items merely *named* "Omada"
   (e.g. the Omada EV) from the omada_self candidates. No-op offline.
3. **select / 初筛** (`engine/select.py`) — Python rule-based coarse filter (the gate that fixed "stale content"):
   - **freshness window** (daily 2d / weekly 7d), **provenance-G exempt** (deep-research syntheses);
   - **crosspost-collapse** (same story across subreddits → one);
   - **turning-point re-surfacing** (heat spike / sentiment flip / switch-intent, after cooldown);
   - **subject + source balance** (round-robin so omada_self isn't crowded out; G gets its own slot);
   - **wide net** to `NINTEL_SELECT_PREFILTER_MAX` (default 80) — it no longer hard-caps to the
     final count, so a valuable low-engagement signal isn't pre-judged away. Pure-Python and free.
4. **shortlist / 精选** (`engine/shortlist.py` → `llm.shortlist_items`, **Sonnet**) — the value
   judge: given the ~80 candidates + an editorial system prompt (`prompts/shortlist.md`:
   background / goal / filtering strategy), it keeps the ~`NINTEL_SHORTLIST_MAX` (default 15) most
   *decision-relevant* items (value over engagement — a low-engagement firmware-bug thread beats a
   high-like water post). **Selects real items by index only** — never generates (NO-FABRICATION
   holds). Best-effort: a hiccup → prefilter order; offline → prefilter top-N; a Python net
   guarantees omada_self is represented.
5. **classify** (Haiku, `engine/classify.py`) — summary / category / signal_strength on the ~15 精选 items.
6. **curate / 策展** (Opus, `engine/curate.py`) — **synthesis** (see §5). The engine, not the LLM,
   owns: section assembly, `cite_id` assignment (1..N in display order) + References rebuild,
   citation-integrity asserts, reference pruning to the cited set, enum-guarding of LLM drift,
   and a non-empty-lead safety net.
7. **trend** (`engine/trend.py`) — recompute `stats` + the weekly `dashboard` from the curated items.
8. **funnel** — `采集`(raw per source) → `初筛`(select) → `精选`(Sonnet) → `策展`(cited) + byline → `report.funnel`.
9. **review gate** (`review/gate.py`) — daily auto-publishes; weekly lands in `pending/` for `/admin`.
10. **publish** — write `data/published/<id>.json` + upsert the `reports` table (the API serves
   `row.payload` fresh per request); optionally index history into RAG / push a page to kos.

**LLM-optional invariant:** offline (no `NINTEL_LLM_ENABLED`) the curate stage replays the
seed manifest → byte-stable output → the test suite runs with no keys/network. Synthesis,
insights, and the funnel only materialize on the **live + LLM** path.

## 4. The contract (`report.json`)

`additionalProperties:false` at the top; evolution is **right-extend only** (add optional
fields; never break cite numbering or add a `SectionKey` the frontend can't render). Mirrored
in `contract.py` (Pydantic `extra="forbid"`) and `types.ts`.

**v1.4 additions (all optional, backward-compatible):**
- `insights[]` — synthesized thematic entries `{id, subject, title, body, takeaway, cite_refs}`.
- `sections[].insights` — insight-id refs (when present, the frontend renders these, not per-item cards).
- `funnel` — `{collected[], refined, curated, byline, tz}` for the subtitle.

## 5. Curation = synthesis (not per-item)

The report body is **section-grouped synthesized insights**: each combines several related
signals into one theme (`①②③`), adds a `💡` takeaway, and cites the underlying real items
academically (a `来源` line of source-glyph chips → the bottom References). The raw per-source
items remain as the **References** and the `全部条目` stream.

Three persisted stores, two of them "raw":
- **Firehose** `intel_items` (~thousands): every ingested signal + dedup/heat state. Not in the UI.
- **Extraction** `report.items[]` (the cited subset): per-source summary/category/impact + URL. In `全部条目`.
- **Synthesis** `report.insights[]`: cites items by `cite_id` (no duplication).

Subject-aware impact (PRD §2.1): `omada_self → needs_fix|feature_input|strength_confirm`,
`competitor → threat|opportunity|neutral`, `industry → opportunity|neutral`.

## 6. State & persistence (`store/`)

SQLite (`data/nintel.db`, WAL): `intel_items` (firehose + per-item lifecycle: first/last_seen,
last_reported_at, report_count, peak/last_heat, last_sentiment, switch_intent, state),
`heat_snapshots` (time series for spike detection), `item_reports` (item↔report junction),
`reports` (published payloads served by the API). Join key everywhere is `content_hash`.

## 7. RAG / kos (`engine/rag.py`, `engine/gbrain.py`)

Optional (`NINTEL_RAG_ENABLED` + `llm_enabled`). Two collections: `background` (Omada/competitor
domain knowledge — local `knowledge/*.md` corpus **or** the **kos** knowledge base via
`NINTEL_KB_BACKEND=gbrain`) and `history` (past reported items, local sqlite-vec). The curator
receives `context.background` + `context.prior_coverage` as **reference-only** input — it
sharpens analysis and flags "already covered / turning point", but is never citeable. kos is
reached over OAuth 2.1 + MCP `search`; READ works, WRITE (`put_page`) currently fails server-side.

## 8. Frontend (`apps/web`)

Dossier-system reader. Pages: Home · Daily · Weekly (+ Store table & dashboard) · Archive ·
All Items. `ReportView` renders the funnel subtitle, the lead, section-grouped `InsightEntry`
cards (with source-glyph `来源` chips), the weekly `StrategyBlock`, and the References. The
**admin console** (`/admin`, password-gated, `AdminPage.tsx`) reuses `ReportView` for a live
preview while an operator edits directly or via LLM chat, then publishes. Consumes the REST
API; falls back to `contract/*.json` seeds offline.

## 9. Deploy & environments

- **Production:** pm2 (`nintel-api`, `nintel-web`, `nintel-dev`) + Cloudflare tunnel
  (`daily.omada.ink` → :5173). Data fixes need no redeploy (API reads the DB per request);
  frontend changes need `npm run build` + `pm2 restart nintel-web`.
- **Offline / CI:** no keys, no network — fixture connectors + seed-manifest curate; `make test`.
- **Real regen:** `scripts/regen_synth.py` builds against a throwaway state DB then publishes
  to main (so the production state machine is never mutated by a re-run).
