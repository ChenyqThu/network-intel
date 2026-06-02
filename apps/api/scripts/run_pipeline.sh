#!/bin/sh
# Scheduled nintel report build (launchd/cron entrypoint).
#
#   run_pipeline.sh daily --publish     # daily: build + auto-publish
#   run_pipeline.sh weekly              # weekly: build -> pending (manual review)
#
# Operational env (live sources, LLM, RAG) is set by the launchd plist / crontab;
# secrets (ANTHROPIC_API_KEY, SUPABASE_*, NOTION_*) live in apps/api/.env, which
# config.py loads via python-dotenv (WorkingDirectory must be apps/api).
set -eu

API_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # .../apps/api
LOG_DIR="${NINTEL_LOG_DIR:-$HOME/Library/Logs/nintel}"
mkdir -p "$LOG_DIR"

TYPE="${1:?usage: run_pipeline.sh <daily|weekly> [--publish]}"
shift

cd "$API_DIR"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] build --type $TYPE $*" >> "$LOG_DIR/$TYPE.log"
exec "$API_DIR/.venv/bin/python" -m nintel.pipeline build --type "$TYPE" "$@" \
    >> "$LOG_DIR/$TYPE.log" 2>&1
