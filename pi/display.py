"""Thin wrapper around the Waveshare 5.65in ACeP panel.

Keeping the hardware behind one module means the display loop can be run and
tested on a normal computer with EPAPER_DRY_RUN=1, and means there is exactly
one place that knows how to put the panel back to sleep.
"""

import logging
from PIL import Image

from pi import config

logger = logging.getLogger(__name__)

try:
    from waveshare_epd import epd5in65f
except ImportError:  # not on the Pi, or the driver was never installed
    epd5in65f = None


class PanelUnavailableError(RuntimeError):
    """Raised when the Waveshare driver is missing and dry-run is not enabled."""


def _require_driver():
    if epd5in65f is None:
        raise PanelUnavailableError(
            "waveshare_epd is not installed. Install it into the venv with "
            "'.venv/bin/pip install ~/e-Paper/RaspberryPi_JetsonNano/python', "
            "or set EPAPER_DRY_RUN=1 to run without a panel."
        )


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
            logger.warning(
                "%s is %dx%d, expected %dx%d - resizing to fit",
                image_path.name, image.width, image.height,
                config.PANEL_WIDTH, config.PANEL_HEIGHT,
            )
            image = image.resize((config.PANEL_WIDTH, config.PANEL_HEIGHT))

        panel = epd5in65f.EPD()
        try:
            panel.init()
            panel.Clear()
            panel.display(panel.getbuffer(image))
            logger.info("Displayed %s", image_path.name)
        finally:
            panel.sleep()


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
