"""Settings for the onboard display loop.

Every value can be overridden with an environment variable, which means the
systemd unit can change behaviour without editing code. Defaults assume the
layout created by the re-imaging runbook: everything under ~/epaper.
"""

import os
from pathlib import Path


def _env_path(name, default):
    return Path(os.environ.get(name, default)).expanduser()


def _env_int(name, default):
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


# Photos and other state live OUTSIDE the git working tree on purpose. A deploy
# does 'git reset --hard' on ~/epaper, so anything kept in there is one bad
# deploy away from being wiped.
EPAPER_DATA = _env_path("EPAPER_DATA", Path.home() / "epaper-data")

# Photos land here, written by the sender script or by an rclone sync. Files may
# be partially written at any moment, so the loop never reads this directly.
INCOMING_DIR = _env_path("EPAPER_INCOMING", EPAPER_DATA / "photos")

# A mirror of INCOMING_DIR that the loop reads from. Mirroring happens between
# display cycles, so a half-transferred file is never handed to the panel.
DISPLAY_DIR = _env_path("EPAPER_DISPLAY", EPAPER_DATA / "display")

# Seconds each photo stays on the panel. The 5.65in ACeP panel takes ~30s to
# refresh and the manufacturer advises against refreshing more than necessary,
# so keep this generous.
DISPLAY_SECONDS = _env_int("EPAPER_DISPLAY_SECONDS", 60 * 3)

# Seconds to wait before retrying after an unexpected error.
ERROR_RETRY_SECONDS = _env_int("EPAPER_ERROR_RETRY_SECONDS", 60 * 10)

# Quiet hours, as local-time hours on a 24h clock. The panel holds its last
# image while paused - e-paper needs no power to keep displaying.
# Pausing from 0 up to (but not including) 8 means 00:00-07:59 inclusive.
PAUSE_FROM_HOUR = _env_int("EPAPER_PAUSE_FROM_HOUR", 0)
PAUSE_UNTIL_HOUR = _env_int("EPAPER_PAUSE_UNTIL_HOUR", 8)

# How long to sleep between checks while paused overnight.
PAUSE_POLL_SECONDS = _env_int("EPAPER_PAUSE_POLL_SECONDS", 60 * 10)

# A photo must have gone this long without being modified before it is treated
# as fully transferred. Guards against picking up a half-written upload.
STABLE_SECONDS = _env_int("EPAPER_STABLE_SECONDS", 30)

# Panel dimensions, used to validate images before sending them to the display.
PANEL_WIDTH = 600
PANEL_HEIGHT = 448

# Set EPAPER_DRY_RUN=1 to run the loop on a machine with no panel attached.
DRY_RUN = os.environ.get("EPAPER_DRY_RUN", "") not in ("", "0", "false", "False")
