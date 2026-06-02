# Architecture Decision Record

## ADR-1 — `report.json` as the single contract
PRD v1.3 §7.9 mandates one engine↔frontend contract. We freeze it as a JSON Schema
(`contract/report.schema.json`) and validate on **both** sides (Pydantic models in the
backend, TS types + shape tests in the frontend). The engine's only product is `report.json`;
web / email / Feishu all render the same document. This decouples frontend redesigns from
engine source changes and lets each side develop against fixtures.

## ADR-2 — Backend: Python + FastAPI + SQLite
Matches SOLUTION §8 (`connectors/` → `engine/{ingest,classify,curate,trend,render}` → SQLite
`nintel.db`). FastAPI serves the contract over REST and renders email HTML from the same data.
Pydantic v2 models *are* the schema at the boundary.

## ADR-3 — Frontend: React + Vite + TypeScript
The design medium is a React/Babel prototype; Vite+TS is the faithful production port. We port
`project/styles.css` verbatim (pixel parity) and add the v2/v3 component tokens from
`project/ds/ds.css`. No visual redesign — this is an implementation of an approved design.

## ADR-4 — Offline-first / fixture-backed connectors
The real upstreams (UNIFI_CHANNELS Supabase, omada-sentiment-monitor Notion) and their
credentials are **not present** in this environment. Connectors expose the exact interface a
live Supabase/Notion reader would, but ship fixture implementations seeded from the
human-verified SAMPLE_REPORT data. `NINTEL_CONNECTOR_MODE=live` is the drop-in seam.

## ADR-5 — LLM curation is real but optional
PRD FR-2 specifies a two-tier pipeline (Haiku summarize → Opus curate). It's implemented with
the Anthropic SDK + prompt caching, gated behind `NINTEL_LLM_ENABLED` (default off). Shipped
reports use the deterministic curated seed so the system runs and tests fully offline, with no
API keys and no network.

## ADR-6 — Subject-aware impact semantics (handoff v2)
`subject` decides the section AND the impact vocabulary:
`omada_self → needs_fix | feature_input | strength_confirm`; `competitor → threat | opportunity | neutral`.
The frontend `ImpactPill`/`Research` switch labels + tones accordingly.

## Reviews
- Frontend reviewed by an Opus reviewer.
- Backend: the requested Codex / GPT-5.5 reviewer is **not available** in this environment;
  substituted with a rigorous high-effort Opus backend review (noted here for transparency).
