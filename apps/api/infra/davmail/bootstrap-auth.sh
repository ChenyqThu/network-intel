#!/bin/sh
# One-time (re-)authentication for davmail's OAuth token. Normally you NEVER run
# this — token.dat persists and auto-refreshes. Use it only if token.dat is lost
# or invalidated (device removed from tenant, long idle, password reset).
#
#   ./bootstrap-auth.sh lucien.chen@omadanetworks.com '<cipher-key>'
#
# The cipher key is a string YOU choose; it encrypts token.dat and becomes the
# SMTP/IMAP login password (NINTEL_DAVMAIL_CIPHER_KEY). It is NOT the O365 password.
#
# Flow: davmail prints an OAuth URL; you sign in (account + MFA + Continue); then
# you copy the authorization code and paste it back here. IMPORTANT for this tenant:
# the redirect is OOB (urn:ietf:wg:oauth:2.0:oob), so after Continue the browser
# lands on a blank/error page and the code is NOT shown — open DevTools -> Network,
# find the failed request whose URL starts with "urn:ietf:wg:oauth:2.0:oob?code=...",
# and copy that whole URL. Codes expire fast, so do it promptly.
set -eu

EMAIL="${1:?usage: bootstrap-auth.sh <email> <cipher-key>}"
KEY="${2:?usage: bootstrap-auth.sh <email> <cipher-key>}"
DIR="$(cd "$(dirname "$0")" && pwd)"
IMG=eclipse-temurin:17-jre
FIFO="$(mktemp -u "${TMPDIR:-/tmp}/davmail-boot.XXXXXX")"
LOG="$(mktemp "${TMPDIR:-/tmp}/davmail-boot.XXXXXX.log")"

if [ ! -f "$DIR/davmail.jar" ]; then
  echo "davmail.jar missing — run ./fetch-davmail.sh first" >&2
  exit 1
fi

cleanup() { exec 9>&- 2>/dev/null || true; docker rm -f nintel-davmail-boot >/dev/null 2>&1 || true; rm -f "$FIFO"; }
trap cleanup EXIT

mkfifo "$FIFO"
docker rm -f nintel-davmail nintel-davmail-boot >/dev/null 2>&1 || true

# davmail reads the auth code from stdin; feed stdin from the fifo we hold open.
docker run -i --rm --name nintel-davmail-boot \
  -p 127.0.0.1:1025:1025 -p 127.0.0.1:1143:1143 \
  -v "$DIR":/davmail -w /davmail "$IMG" \
  java -jar davmail.jar /davmail/davmail.properties < "$FIFO" > "$LOG" 2>&1 &
exec 9>"$FIFO"

i=0; while ! grep -q "listening on SMTP" "$LOG" 2>/dev/null; do
  sleep 1; i=$((i+1)); [ "$i" -gt 40 ] && { echo "davmail failed to start; see $LOG" >&2; exit 1; }
done

# A login triggers davmail to print the authorize URL and block reading the code.
( python3 - "$EMAIL" "$KEY" <<'PY'
import imaplib, socket, sys
socket.setdefaulttimeout(1500)
try:
    imaplib.IMAP4("127.0.0.1", 1143).login(sys.argv[1], sys.argv[2])
except Exception:
    pass
PY
) >/dev/null 2>&1 &

i=0; while ! grep -q "oauth2/authorize" "$LOG" 2>/dev/null; do
  sleep 1; i=$((i+1)); [ "$i" -gt 40 ] && { echo "no authorize URL emitted; see $LOG" >&2; exit 1; }
done

echo
echo "=============================================================================="
echo "1) Open this URL in a browser, sign in (account + MFA), click Continue:"
echo
grep -o 'https://login.microsoftonline.com[^ ]*oauth2/authorize[^ ]*' "$LOG" | head -1
echo
echo "2) After Continue the browser shows a blank/error page. Open DevTools (F12)"
echo "   -> Network, find the failed request starting with:"
echo "        urn:ietf:wg:oauth:2.0:oob?code=..."
echo "   Copy that ENTIRE URL. The code is NOT on the page and expires fast."
echo "=============================================================================="
printf "3) Paste the urn:...?code=... URL and press Enter:\n> "
read -r RESP
printf '%s\n' "$RESP" >&9

i=0; while [ "$i" -lt 40 ]; do
  if grep -q "Authenticated username" "$LOG" 2>/dev/null; then break; fi
  if grep -qE "invalid_grant|AADSTS|Authentication failed" "$LOG" 2>/dev/null; then
    echo "FAILED:"; grep -oE "AADSTS[0-9]+[^\"]*" "$LOG" | tail -1; exit 1
  fi
  sleep 1; i=$((i+1))
done

if [ -s "$DIR/token.dat" ]; then
  echo "OK: token.dat written ($(wc -c < "$DIR/token.dat" | tr -d ' ') bytes)."
  echo "Start davmail normally: pm2 restart nintel-davmail   (or ./run-davmail.sh)"
else
  echo "token.dat NOT written — the code likely expired. Re-run and paste faster." >&2
  exit 1
fi
