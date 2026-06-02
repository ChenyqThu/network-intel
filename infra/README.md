# infra — scheduled report generation

The long-running services (`nintel-api` :8000, `nintel-web` :5173) are managed by
**pm2** (`ecosystem.config.cjs`). Report *generation* is a separate **batch** job
run on a schedule by **launchd** (primary) or **cron** (fallback). It writes to
the same `apps/api/data/nintel.db`; because the API reads the DB live, a published
report shows up on the next request — no restart needed.

## Cadence
- **Daily** 08:30 → `build --type daily --publish` (auto-published).
- **Weekly** Monday 09:00 → `build --type weekly` → `data/pending/` for manual
  review. Approve with:
  ```sh
  cd apps/api && .venv/bin/python -m nintel.pipeline approve <report_id>
  ```

## Prerequisites
1. `make install` (backend venv + deps). For live + LLM + RAG also install extras:
   ```sh
   cd apps/api && .venv/bin/pip install -e '.[llm,rag,live]'
   ```
2. Secrets in `apps/api/.env` (copy from `.env.example`): `ANTHROPIC_API_KEY`,
   `SUPABASE_URL`/`SUPABASE_KEY`, `NOTION_TOKEN`/`NOTION_DATABASE_ID`,
   `NINTEL_RSS_FEEDS`. The plists/crontab set only non-secret flags; secrets are
   loaded from `.env` via python-dotenv (WorkingDirectory is `apps/api`).
3. First RAG build: `cd apps/api && .venv/bin/python -m nintel.pipeline kb reindex`.

## launchd (primary, macOS)
```sh
cp infra/launchd/ink.omada.nintel.daily.plist  ~/Library/LaunchAgents/
cp infra/launchd/ink.omada.nintel.weekly.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ink.omada.nintel.daily.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ink.omada.nintel.weekly.plist
# trigger once to verify:
launchctl kickstart -k gui/$(id -u)/ink.omada.nintel.daily
# logs: ~/Library/Logs/nintel/{daily,weekly}.log
```
Edit the absolute paths in the plists if your checkout differs.

## cron (fallback)
```sh
crontab infra/cron/nintel.crontab   # or paste into `crontab -e`
```

## Reboot persistence
launchd survives reboots once bootstrapped. (pm2 services persist via
`pm2 save` + `pm2 startup`.)
