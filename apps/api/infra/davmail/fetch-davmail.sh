#!/bin/sh
# Download + unpack the davmail 6.8.0 cross-platform JAR bundle into this dir.
# The jar/lib are gitignored (large), so a fresh checkout needs this once before
# run-davmail.sh / bootstrap-auth.sh can start the container.
#
#   ./fetch-davmail.sh
#
# Idempotent: skips the download if davmail.jar already exists.
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION=6.8.0
BUILD=4181
ZIP="davmail-${VERSION}-${BUILD}.zip"
URL="https://downloads.sourceforge.net/project/davmail/davmail/${VERSION}/${ZIP}"

if [ -f "$DIR/davmail.jar" ] && [ -d "$DIR/lib" ]; then
  echo "davmail.jar + lib/ already present — nothing to do."
  exit 0
fi

echo "Downloading $URL ..."
curl -fsSL -o "$DIR/$ZIP" "$URL"
echo "Unpacking ..."
unzip -q -o "$DIR/$ZIP" -d "$DIR"
rm -f "$DIR/$ZIP"

if [ -f "$DIR/davmail.jar" ]; then
  echo "Done: davmail ${VERSION}-${BUILD} ready in $DIR"
else
  echo "ERROR: davmail.jar not found after unpack" >&2
  exit 1
fi
