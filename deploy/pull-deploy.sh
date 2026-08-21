#!/bin/bash
# Pull the latest code from GitHub and restart the frame if anything changed. Run on a timer by epaper-update.timer.
set -euo pipefail

REPO="${EPAPER_REPO:-$HOME/epaper}"

cd "$REPO"

before=$(git rev-parse HEAD)
git fetch --quiet origin main
after=$(git rev-parse origin/main)

if [ "$before" = "$after" ]; then
    exit 0
fi

echo "Updating ${before:0:8} -> ${after:0:8}"
git reset --hard --quiet origin/main

if [ -s requirements-pi.txt ]; then
    "$REPO/.venv/bin/pip" install -q -r requirements-pi.txt
fi

chmod +x "$REPO"/deploy/*.sh 2>/dev/null || true

sudo systemctl restart epaper
logger -t epaper-deploy "updated ${before:0:8} -> ${after:0:8}"
echo "Deployed ${after:0:8}"
