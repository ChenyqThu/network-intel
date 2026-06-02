# Network Intel (`nintel`) — Architecture & Implementation Plan

> Full-stack implementation of the **Network Intel** internal competitive-intelligence
> station, derived from the latest authoritative docs in `project/uploads/`:
> **PRD v1.3** (`PRD-404ea141.md`), **SOLUTION v1.3** (`SOLUTION-8ae5d9e6.md`),
> **SAMPLE_REPORT** (`SAMPLE_REPORT-00372eff.md`), **DESIGN_HANDOFF v2 + v3**.
> Visual language: the **"Dossier"** design system shipped in `project/styles.css` +
> `project/components.jsx` and documented in `project/Network Intel Design System.html`.

---

## 1. What we are building

An internal-only competitive & sentiment intelligence reader for the TP-Link network
products team. Two report cadences:

- **Daily** (minimal): `Omada self-sentiment → Competitor moves → Competitor sentiment → Industry`.
- **Weekly** (deep): `🎯 Market-Strategy Insight (pinned) → Omada self → Competitor moves →
  Competitor sentiment → Store moves → Industry → Analytics dashboard`.

The product's soul (PRD §7.8) is **one-click traceability**: every card carries a
prominent citation line, every synthesized conclusion (lead / strategy) carries clickable
`{{cite:N}}` superscripts, and every report ends with a numbered References list.

The entire system is wired around **one contract**: `report.json` (PRD §7.9). The engine
produces it; every frontend (web / email / Feishu) only renders it. See `contract/`.

## 2. Tech-stack decision (evaluated)

| Layer | Choice | Why |
|-------|--------|-----|
| **Contract** | `report.json` + JSON Schema (`contract/report.schema.json`) | PRD §7.9 mandates a single engine↔frontend contract. Schema makes it testable on both sides. |
| **Backend** | **Python 3.11 + FastAPI + SQLite (SQLAlchemy) + Pydantic v2** | Matches SOLUTION §8 (`connectors/`, `engine/ingest|classify|trend|render`, SQLite `nintel.db`). FastAPI serves the contract over REST and can also dump static JSON for CF Pages parity. Pydantic models *are* the schema, validated at the boundary. |
| **LLM stage** | **Anthropic SDK** — Haiku (summarize/classify) + Opus (curate/impact/lead/strategy), with prompt caching | PRD FR-2 two-tier pipeline. Gated behind `NINTEL_LLM_ENABLED`; defaults to the seeded curated fixtures so the system runs and tests **offline / without API keys**. |
| **Connectors** | Interface + **fixture-backed** impl seeded from the verified SAMPLE_REPORT data | The real upstreams (UNIFI_CHANNELS Supabase, omada-sentiment-monitor Notion) and their credentials are **not present in this environment**. Connectors expose the exact shape a real Supabase/Notion reader would, so swapping in live readers is a drop-in. |
| **Frontend** | **React 18 + Vite + TypeScript** | The design medium is a React/Babel prototype; Vite+TS is the production-faithful port. Pixel-parity by porting `styles.css` verbatim as the design-system stylesheet. |
| **Email** | Jinja2 server-rendered template in the backend `render` stage | SOLUTION §8 `templates/daily.html.j2`. Ports `project/email-daily.html` to table-based inline-styled HTML driven by the same contract. |
| **Tests** | `pytest` (backend), `vitest` + Playwright smoke (frontend) | Contract round-trip, schema validation, render snapshots; web build + a headless render check. |

### Repository layout

```
~/Projects/network-intel/
├── ARCHITECTURE.md            ← this file
├── contract/                  ← the engine↔frontend contract (source of truth)
│   ├── report.schema.json     ← JSON Schema (PRD §7.9 + v1.3 strategy/subject)
│   ├── 2026-06-01-daily.json  ← seed: real, link-verified daily (omada_self + competitor + sentiment + industry)
│   └── 2026-W22-weekly.json   ← seed: weekly with strategy block + 7 sections + dashboard stats
├── apps/
│   ├── api/                   ← Python FastAPI backend (engine + REST + email render)
│   └── web/                   ← React + Vite + TS frontend (Dossier design system)
├── docs/                      ← engineering docs (contract guide, dev/run, decisions)
└── project/                   ← original Claude Design handoff (prototype + uploads) — reference
```

## 3. Backend design (`apps/api`)

```
connectors/        SupabaseReader (B), SentimentMonitorReader (A, Notion), RssReader (C)
                   → all behind a Connector protocol; fixture impls seeded from SAMPLE_REPORT
engine/
  ingest.py        normalize each source → Intel Item schema → SQLite (dedupe by content_hash)
  classify.py      Haiku: summary + category + signal_strength (LLM-optional; fixture fallback)
  curate.py        Opus: select/order, omada_impact (subject-aware), impact_note, lead,
                   strategy (weekly), cite_id assignment  → report.json  (LLM-optional)
  trend.py         weekly analytics: by_source / by_impact / sentiment trend / pains / top_hot
  render.py        Jinja2 → daily.html.j2 / weekly.html.j2 email + markdown (Feishu)
  contract.py      Pydantic models == report.json schema; validate() + dump()
store/             SQLAlchemy models (intel_items, reports), session, migrations-lite
api/               FastAPI app: GET /api/reports, /api/reports/{id}, /api/items (filters),
                   /api/archive, GET /api/reports/{id}/email (rendered HTML)
review/            human-review gate: pending dir, approve→publish (PRD §3.2b)
```

**subject-aware impact semantics** (PRD §2.1, handoff v2):
- `subject = omada_self` → `needs_fix` / `feature_input` / `strength_confirm`
- `subject = competitor` → `threat` / `opportunity` / `neutral`

The Intel Item carries the §7.8.5 traceability fields (`url`, `source_domain`,
`source_tier`, `cite_id`, `date`) and v1.3 sentiment fields (`sentiment`,
`relevance`, `switch_intent`). URL integrity follows §7.8.6 (full UUIDs, never truncated).

## 4. Frontend design (`apps/web`)

Pixel-faithful port of the Dossier system. Pages (PRD §7.3): **Home** (latest, daily/weekly
tab) · **Daily** · **Weekly** (sections + dashboard) · **Archive** (filters) · **All Items**
(stream). Plus theme (system/light/dark), density, and the Tweaks panel.

Components ported 1:1 from `project/components.jsx` + the DS page, **including the v2/v3
additions** which the old `index.html` lacked:
- `IntelEntry` with subject-aware `ImpactPill` (threat/opp/neutral **+ fix/feat/strength**)
- `SourceBadge` (glyph + credibility tier), `Research` note, **`SentimentMeta`** tags
- mandatory `CitationLine`, `Lead` + tally with clickable `{{cite:N}}`, `References`
- **`StrategyBlock`** (weekly, pinned) — tokens from `project/ds/ds.css` `.strategy`
- section **tones** (`omada_self`/`competitor`/`sentiment`/`industry`), dashboard charts

Data: consumes the backend REST API; in dev/offline it falls back to the `contract/*.json`
seeds (same shape), so the UI is fully demonstrable without the API running.

## 5. Build plan (parallelized via subagents)

1. **Orchestrator (me)**: scaffold + contract (schema + seeds) + docs. ✅ this commit
2. **Backend agent** (Opus, max effort): implement `apps/api` against the contract + tests.
3. **Frontend agent** (Opus, max effort): implement `apps/web` against the contract + tests.
   *(run concurrently — disjoint directories)*
4. **Reviews (mandatory)**: Opus review of `apps/web`; rigorous Opus review of `apps/api`
   (the requested Codex/GPT-5.5 reviewer is not available in this environment — substituting
   a high-effort Opus backend review and noting it).
5. **Integration & local launch**: run API + web, smoke-test the full flow, fix, commit, PR.

## 6. Non-goals / environment notes
- No live Supabase/Notion/Feishu calls (credentials absent) — connectors are fixture-backed
  but interface-complete for drop-in live readers.
- LLM curation is implemented but optional; the shipped reports use the human-verified
  curated seed data so output is deterministic and offline-runnable.
