"""Thin wrapper around the Waveshare 5.65in ACeP panel.

Keeping the hardware behind one module means the display loop can be run and
tested on a normal computer with EPAPER_DRY_RUN=1, and means there is exactly
one place that knows how to put the panel back to sleep.
"""

import logging
import signal
from contextlib import contextmanager

from PIL import Image

from pi import config

logger = logging.getLogger(__name__)

try:
    from waveshare_epd import epd5in65f
except ImportError:  # not on the Pi, or the driver was never installed
    epd5in65f = None

# Photos already warned about for being the wrong size. Resizing does not change
# the file on disk, so the same photo is still wrong on the next rotation.
_warned_about_size = set()

# SIGALRM and setitimer are POSIX-only. On a Windows dev machine the timeout is
# simply not armed; DRY_RUN returns before the panel code either way.
_can_time_out = hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")


class PanelUnavailableError(RuntimeError):
    """Raised when the panel cannot be talked to at all."""


class PanelTimeoutError(RuntimeError):
    """Raised when a refresh does not finish inside the allowed time."""


def _require_driver():
    if epd5in65f is None:
        raise PanelUnavailableError(
            "waveshare_epd is not installed. Install it into the venv with "
            "'.venv/bin/pip install --no-deps ~/e-Paper/RaspberryPi_JetsonNano/python', "
            "or set EPAPER_DRY_RUN=1 to run without a panel."
        )


def _on_alarm(_signum, _frame):
    raise PanelTimeoutError(
        f"the panel did not finish refreshing within "
        f"{config.PANEL_TIMEOUT_SECONDS}s"
    )


@contextmanager
def _refresh_timeout(seconds):
    """
    Put a ceiling on how long a block may spend talking to the panel.

    Falls through untimed if the alarm cannot be armed, which is better than
    refusing to draw anything at all.
    """
    if not _can_time_out or seconds <= 0:
        yield
        return

    try:
        previous = signal.signal(signal.SIGALRM, _on_alarm)
    except ValueError:
        # Signals can only be hooked from the main thread.
        logger.debug("Not the main thread, running the refresh untimed")
        yield
        return

    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        # None means the previous handler was not installed from Python, and
        # handing that back to signal() raises - inside a finally that may be
        # unwinding a real panel error, which would then be lost.
        if previous is not None:
            signal.signal(signal.SIGALRM, previous)


def show(image_path):
    """
    Draw a single bitmap onto the panel.

    The panel is initialised, written to and put back to sleep on every call.
    Leaving an ACeP panel powered between refreshes risks damaging it, so the
    sleep in the finally block is not optional.

    Parameters:
        image_path (Path): Path to the bitmap to display.

    Returns:
        None
    """
    if config.DRY_RUN:
        logger.info("Dry run, would display %s", image_path.name)
        return

    _require_driver()

    with Image.open(image_path) as image:
        if image.size != (config.PANEL_WIDTH, config.PANEL_HEIGHT):
            if image_path.name not in _warned_about_size:
                _warned_about_size.add(image_path.name)
                logger.warning(
                    "%s is %dx%d, expected %dx%d - resizing to fit",
                    image_path.name, image.width, image.height,
                    config.PANEL_WIDTH, config.PANEL_HEIGHT,
                )
            image = image.resize((config.PANEL_WIDTH, config.PANEL_HEIGHT))

        panel = epd5in65f.EPD()
        try:
            with _refresh_timeout(config.PANEL_TIMEOUT_SECONDS):
                # init() reports failure by returning -1 rather than raising.
                # Ignoring it means carrying on against a panel that is not
                # there and blocking on a BUSY line that will never go high.
                if panel.init() != 0:
                    raise PanelUnavailableError(
                        "the panel did not initialise - check the ribbon cable "
                        "and that SPI is enabled"
                    )

                # No Clear() first. On this panel Clear() is a complete refresh
                # cycle of its own, so clearing then drawing costs two full
                # refreshes - double the power, double the panel wear and twice
                # the exposure to a wedged BUSY line - for an image that
                # display() fully overwrites anyway.
                panel.display(panel.getbuffer(image))

            # Debug, not info: this is the one thing that happens on every
            # single cycle, and at info it is the whole steady-state log volume.
            logger.debug("Displayed %s", image_path.name)
        finally:
            # Swallowed on purpose: this runs while a real failure may already
            # be propagating, and raising here would replace that error with a
            # less useful one.
            try:
                panel.sleep()
            except Exception as error:
                logger.warning("Could not put the panel to sleep: %s", error)


def sleep():
    """
    Put the panel into its low-power state.

    Called on shutdown so that stopping the service leaves the hardware in a
    safe state rather than mid-refresh.

    Returns:
        None
    """
    if config.DRY_RUN or epd5in65f is None:
        return

    try:
        epd5in65f.EPD().sleep()
    except Exception as error:  # shutdown path, never raise
        logger.warning("Could not put the panel to sleep: %s", error)
