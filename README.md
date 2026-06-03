# Network Intel (`nintel`)

An internal competitive & sentiment intelligence station for the TP-Link network products
team. **Daily** (舆情: Omada self-sentiment + competitor moves) + **weekly** deep dives
(+ industry trends, Store moves, analytics) — every signal tagged with its meaning for
Omada, and **every conclusion one-click traceable** to a real source.

> Live: **`daily.omada.ink`**. Conventions & ops for AI sessions: **`CLAUDE.md`**.
> Architecture: **`ARCHITECTURE.md`**. Decisions: `docs/DECISIONS.md`. Contract: `docs/CONTRACT.md`.

## Architecture at a glance

```
sources:  A omada-sentiment (Reddit/YouTube · Notion)   B UNIFI_CHANNELS Supabase (+Store)
          C industry RSS (weekly)                         G Gemini deep-research (weekly)
   → ingest → SQLite → brand → select 初筛(freshness + dedup + balance, wide net)
       → Sonnet 精选(value-select) → classify(Haiku) → curate(Opus: synthesize insights + lead)
       → trend → funnel → review gate (daily auto · weekly → /admin) → publish → report.json   ← THE CONTRACT
           → render (web · email)   ·   optional RAG background from kos
```

One contract drives everything: **`report.json`**. The backend produces it; every frontend
only renders it. Schema lives in `contract/report.schema.json`, mirrored by
`apps/api/src/nintel/contract.py` (Pydantic) and `apps/web/src/types.ts` (TS).

| Part | Stack | Location |
|------|-------|----------|
| Contract | JSON Schema + seed reports | `contract/` |
| Backend (engine + REST + email) | Python · FastAPI · SQLite · Pydantic v2 · Jinja2 | `apps/api/` |
| Frontend (reader + admin console) | React 18 · Vite · TypeScript | `apps/web/` |

## Quick start (local)

```bash
make install     # backend venv + seed, frontend node_modules
make api          # FastAPI on http://localhost:8000   (terminal 1)
make web          # Vite on  http://localhost:5173      (terminal 2; proxies /api → :8000)
make test         # backend pytest + frontend vitest (offline, no keys needed)
```

Open <http://localhost:5173>. The web app reads the live API; if it's down it falls back to
the bundled contract seeds, so the UI is demonstrable standalone.

- Engine CLI: `python -m nintel.pipeline build --type daily|weekly` (offline = deterministic seed).
- Real regen (live + LLM + kos): `cd apps/api && .venv/bin/python scripts/regen_synth.py`.
- Email preview: `GET http://localhost:8000/api/reports/<id>/email`.

## What's implemented

- **Synthesized curation (v1.4)** — the report body is **section-grouped thematic insights**
  that combine multiple signals (标题 + 综述 + 💡研判 + 来源), citing real items academically;
  raw per-source items become the bottom References. Not per-message readings.
- **Provenance funnel** in the subtitle — `采集(各源) → 精炼 → 策展 N 条 · 时间 · 署名`.
- **Freshness gate** — daily 2-day / weekly 7-day window; kills stale/undated leakage
  (deep-research source G is exempt by design).
- **Subject-aware impact** — `omada_self → 待修复/功能需求/优势确认`,
  `competitor → 威胁/机会/中性`, `industry → 机会/中性`.
- **Citation-first** — clickable `{{cite:N}}`, end-of-report References, full-UUID URL integrity.
- **Value-based 精选 (Sonnet)** — Python casts a wide rule-based 初筛 net (~80), then **Sonnet**
  value-selects the ~15 most decision-relevant signals (value over engagement), so a critical
  low-engagement post isn't dropped by heuristics. It selects real items only (no fabrication).
- **Live + three-tier LLM** — A/B/C/G connectors (`NINTEL_CONNECTOR_MODE=live`) + Sonnet(精选)
  → Haiku(classify) → Opus(curate) (`NINTEL_LLM_ENABLED`), with prompt caching. Offline fixture
  mode stays deterministic for tests.
- **kos / RAG background** — optional Omada domain knowledge from the kos knowledge base fed
  to the curator as reference-only context (`NINTEL_RAG_ENABLED` + `NINTEL_KB_BACKEND=gbrain`).
- **Admin review console** — `/admin` (password-gated): review pending weeklies, edit directly
  or via LLM chat with live preview, then publish.
- **Pages** — Home · Daily · Weekly (+ Store table & analytics dashboard) · Archive · All Items;
  theme (system/light/dark), density, Tweaks.

## Deploy (production)

pm2 daemons + a Cloudflare tunnel (`ecosystem.config.cjs`):

- `nintel-api` :8000 · `nintel-web` :5173 (vite preview of `dist/`) · `nintel-dev` :5174 (HMR, local).
- `daily.omada.ink` → :5173. The API reads the DB fresh per request, so **data fixes need no
  redeploy** (just refresh); **frontend changes need `npm run build` + `pm2 restart nintel-web`**.

Daily auto-publishes; the **weekly lands in `/admin` as pending** for human review before publish.

## Layout

```
contract/   report.schema.json · seed daily/weekly · archive.json
apps/api/   src/nintel/{connectors,engine,store,review,api,templates} · prompts · knowledge · scripts · tests
apps/web/   src/{components,pages,lib,api,styles,fixtures,test} · vite + ts
docs/       CONTRACT.md · DECISIONS.md · PRD.md · SOLUTION.md · HANDOFF_README.md
project/    original Claude Design handoff (prototype + uploads) — reference
```
