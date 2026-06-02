# Network Intel — Web (`apps/web`)

Frontend for the **Network Intel** (`nintel`) internal competitive-intelligence
station. React 18 + Vite + TypeScript, with the **"Dossier"** design system
ported pixel-faithfully into `src/styles/dossier.css` (tokens, class names and
values kept identical to `project/styles.css` + the v2/v3 `project/ds/ds.css`
additions).

Every frontend (web / email / Feishu) only **renders the one contract**:
`report.json` (PRD v1.3 §7.9, schema in `contract/report.schema.json`). This app
consumes it over a REST API and falls back to bundled fixtures when offline.

## Pages (real routes)

| Route      | Page                                                              |
| ---------- | ----------------------------------------------------------------- |
| `/`        | Home — latest report, daily/weekly segmented toggle (defaults daily), sticky TOC |
| `/daily`   | Latest daily report                                               |
| `/weekly`  | Latest weekly report (StrategyBlock + sections + store + dashboard) |
| `/archive` | History list with search + type chips (日报/周报) + theme chips    |
| `/items`   | All-items stream: time-grouped, filters (subject / source / impact / search) |

## Setup / run / build / test

```bash
cd apps/web
npm install        # install dependencies
npm run dev        # dev server at http://localhost:5173 (proxies /api -> :8000)
npm run build      # tsc -b && vite build  (must pass with no type errors)
npm run test       # vitest run (unit + render smoke)
npm run preview    # preview the production build
npm run typecheck  # tsc -b --noEmit
```

## Environment

| Var             | Default | Purpose                                              |
| --------------- | ------- | ---------------------------------------------------- |
| `VITE_API_BASE` | `/api`  | Base URL for the backend REST API.                   |

In dev, Vite proxies `/api` → `http://localhost:8000` (see `vite.config.ts`).

### Offline / fixture fallback

`src/api/client.ts` is a typed fetch client. If any API call fails (no backend),
it transparently serves the bundled contract fixtures in `src/fixtures/` and logs
one console note. The two seed reports (`2026-06-01-daily`, `2026-W22-weekly`)
and the archive index render fully from fixtures alone, so the UI is demonstrable
standalone. A small "离线 · 内置 fixtures" badge shows on Home in that mode.

The email link (`查看原文`-style top-bar / sidebar / footer links) points at the
API endpoint `GET /api/reports/{id}/email` and opens in a new tab.

## Data layer & key utilities

- `src/types.ts` — TypeScript types mirroring `report.schema.json` exactly.
- `src/lib/intel.ts` — **centralized, unit-tested** utilities:
  - `parseCites` / `citeNumbers` — `{{cite:N}}` superscript parsing.
  - `impactMeta` / `impactClass` / `impactLabel` / `researchLabel` / `nodeClass`
    — subject-aware impact mapping for all 7 enums (threat/opportunity/neutral
    + needs_fix/feature_input/strength_confirm + unknown), incl. the wrench/bulb/star
    icons and labels 待修复 / 功能需求 / 优势确认.
  - `SOURCE_REGISTRY` / `sourceGlyph` / `sourceDisplayLabel` / `defaultTierLabel`
    — source glyph + credibility-tier mapping.
- `src/lib/jump.ts` — offset-aware scroll + flash for citation jumps.

## Components (ported 1:1 + v2/v3 additions)

`IntelEntry` (ledger row) with meta rail (mono index + diamond impact node incl.
`n-fix`/`n-feat`/`n-strength`), `SourceBadge`, subject-aware `ImpactPill`,
provenance tags (`来源 A/B/C`) + `SentimentMeta` (情感 / 相关性 / 切换意图),
subject-aware `Research` note, `Metrics`, and the mandatory `CitationLine`.
`Lead` + tally with clickable `{{cite:N}}`, `StrategyBlock` (weekly, pinned,
target icon + OPUS 策展 badge + 依据 ref row), `SectionHead` with `tone-<key>`
section tones, `References`, `ReportHeader`, and the dashboard charts
(`KpiCard` / `Donut` / `SourceBars` / `TrendLine` + pains / vs / store table).

## Theming & Tweaks

Theme (system/light/dark), density (compact/regular/comfy), home layout
(two/single), and chart style (minimal/filled) are controlled by the Tweaks
panel (`useTweaks`), persisted to `localStorage('nintel.tweaks')`. The no-FOUC
script in `index.html` resolves theme + density + primary color before first
paint. Deep-evergreen primary `#0C6151` (light) / `#36A88B` (dark), warm-ivory
paper light theme, ink dark theme, Manrope + mono.

Manrope is loaded via a Google Fonts `<link>` (pragmatic); if it fails the
`--font-sans` system stack takes over without breaking the build.
