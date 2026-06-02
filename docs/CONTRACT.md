# The `report.json` contract

The engine↔frontend contract (PRD v1.3 §7.9). The backend produces `report.json`;
every frontend (web / email / Feishu) only renders it. Validate with
`contract/report.schema.json` (JSON Schema 2020-12).

- `contract/2026-06-01-daily.json` — seed daily (omada_self + competitor + sentiment + industry)
- `contract/2026-W22-weekly.json`  — seed weekly (strategy + 7 sections + dashboard)
- `contract/archive.json`          — report index for the Archive page

Key rules:
- `subject` (omada_self|competitor|industry) drives section + impact semantics:
  omada_self → needs_fix|feature_input|strength_confirm; competitor → threat|opportunity|neutral.
- `sections[].items` reference `items[].id` (order = display order). Items are a flat array
  so one item can be cited by lead/strategy/multiple places without duplication.
- `lead.text` / `strategy.body` / `strategy.paras[][1]` carry `{{cite:N}}` → clickable superscripts.
- Every item has a mandatory citation line: `source_domain · date · 查看原文 ↗` → `url`.
- `references` is the numbered end list; `cite_id` ties items ↔ references ↔ superscripts.
- URL integrity (§7.8.6): community.ui.com URLs keep full UUIDs, never truncated.
