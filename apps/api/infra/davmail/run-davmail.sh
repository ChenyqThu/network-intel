#!/bin/sh
# Run davmail in Docker, foreground, for pm2 to supervise (see ecosystem.config.cjs).
# Bridges local SMTP 1025 / IMAP 1143 (bound to 127.0.0.1 only) to Exchange/O365.
# Requires a one-time auth (token.dat) — see bootstrap-auth.sh / README.md.
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
IMG=eclipse-temurin:17-jre
NAME=nintel-davmail

if [ ! -f "$DIR/davmail.jar" ]; then
  echo "davmail.jar missing — run ./fetch-davmail.sh first" >&2
  exit 1
fi

# Clear any stale container from an unclean previous exit, then run in the
# foreground (--rm) so pm2 owns the lifecycle and cleans up on stop/restart.
docker rm -f "$NAME" >/dev/null 2>&1 || true
exec docker run --rm --name "$NAME" \
  -p 127.0.0.1:1025:1025 -p 127.0.0.1:1143:1143 \
  -v "$DIR":/davmail -w /davmail \
  "$IMG" java -jar davmail.jar /davmail/davmail.properties
