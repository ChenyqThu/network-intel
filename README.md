# Network Intel (`nintel`)

An internal competitive & sentiment intelligence station for the TP-Link network products
team. **Daily** minimal increments + **weekly** deep dives, monitoring **Omada self-sentiment**
(own-product bugs / feature requests / praise), **competitor moves** (UniFi releases / firmware
/ pricing), and **industry** trends — every signal tagged with its meaning for Omada, and
**every conclusion one-click traceable** to its source.

This repository is the full-stack implementation of the product specified in
`project/uploads/` — **PRD v1.3**, **SOLUTION v1.3**, **SAMPLE_REPORT**, and **DESIGN_HANDOFF
v2/v3** — rendered in the approved **"Dossier"** design system.

> Built from the Claude Design handoff bundle (now under `project/`; see
> `docs/HANDOFF_README.md`). Architecture & decisions: `ARCHITECTURE.md`, `docs/DECISIONS.md`.

## Architecture at a glance

```
sources (A sentiment-monitor · B UNIFI_CHANNELS · C industry RSS)
   → ingest → SQLite → classify (Haiku) → curate (Opus) → report.json  ← THE CONTRACT
        → render (web · email · Feishu)   [human-review gate before publish]
```

One contract drives everything: **`report.json`** (PRD §7.9). The backend produces it; every
frontend only renders it. Schema + seeds live in `contract/` and are validated on both sides.

| Part | Stack | Location |
|------|-------|----------|
| Contract | JSON Schema + seed reports | `contract/` |
| Backend (engine + REST + email) | Python · FastAPI · SQLite · Pydantic v2 · Jinja2 | `apps/api/` |
| Frontend (5-page reader) | React 18 · Vite · TypeScript | `apps/web/` |

## Quick start (local)

```bash
make install     # backend venv + seed, frontend node_modules
make api          # FastAPI on http://localhost:8000   (terminal 1)
make web          # Vite on  http://localhost:5173      (terminal 2; proxies /api → :8000)
make test         # backend pytest (48) + frontend vitest (32)
```

Open <http://localhost:5173>. The web app reads the live API; if the API is down it falls back
to the bundled contract seeds, so the UI is fully demonstrable standalone.

- Engine CLI: `make pipeline` → builds `report.json` for daily + weekly.
- Email preview: `GET http://localhost:8000/api/reports/2026-W22-weekly/email`.

## What's implemented (per the latest docs)

- **Subject-aware impact semantics** — `omada_self → 待修复/功能需求/优势确认`,
  `competitor → 威胁/机会/中性` (PRD §2.1, handoff v2).
- **Citation-first** (PRD §7.8) — mandatory citation line per card, clickable `{{cite:N}}`
  superscripts in the lead and the weekly strategy block, end-of-report References list,
  source-tier weighting, full-UUID URL integrity (§7.8.6).
- **Weekly Market-Strategy Insight** — pinned strategy block with "OPUS 策展" badge (handoff v3).
- **Five pages** — Home (daily/weekly), Daily, Weekly (+ analytics dashboard & store table),
  Archive (filters), All Items (stream); theme (system/light/dark), density, Tweaks.
- **Two-tier LLM pipeline** (Haiku summarize → Opus curate) with prompt caching — real but
  optional (`NINTEL_LLM_ENABLED`, default off; ships deterministic curated data).

## Environment notes

The upstream data sources (UNIFI_CHANNELS Supabase, omada-sentiment-monitor Notion) and their
credentials are not present in this sandbox, so connectors are **fixture-backed** with an
interface-complete live drop-in seam (`NINTEL_CONNECTOR_MODE=live`). Reports use the
human-verified SAMPLE_REPORT data. See `docs/DECISIONS.md` (ADR-4/5) for the full rationale.

## Layout

```
contract/   report.schema.json · 2026-06-01-daily.json · 2026-W22-weekly.json · archive.json
apps/api/   src/nintel/{connectors,engine,store,review,api,templates} · prompts · tests
apps/web/   src/{components,pages,lib,api,styles,fixtures,test} · vite + ts
docs/       CONTRACT.md · DECISIONS.md · HANDOFF_README.md
project/    original Claude Design handoff (prototype + uploads) — reference
```
