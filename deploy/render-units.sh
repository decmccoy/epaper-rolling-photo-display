#!/bin/bash
# Render the systemd unit templates for this device and install them.
# Called by install.sh; safe to run on its own after changing EPAPER_REPO.
set -euo pipefail

REPO="${EPAPER_REPO:-$HOME/epaper}"
SERVICE_USER="$(id -un)"

for unit in epaper.service epaper-update.service epaper-update.timer; do
    rendered="$(sed -e "s|__EPAPER_REPO__|$REPO|g" \
                    -e "s|__EPAPER_USER__|$SERVICE_USER|g" \
                    "$REPO/deploy/$unit")"

    # A surviving placeholder means the template drifted. Better to stop than to
    # install a unit pointing at a user that does not exist.
    if printf '%s' "$rendered" | grep -q '__EPAPER_'; then
        echo "ERROR: unsubstituted placeholder left in $unit" >&2
        exit 1
    fi

    printf '%s\n' "$rendered" | sudo tee "/etc/systemd/system/$unit" > /dev/null
done

sudo systemctl daemon-reload
