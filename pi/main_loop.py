"""The display loop that runs continuously on the Pi.

Run it with 'python -m pi.main_loop' so that the 'pi' package is importable.
Under systemd it is started by deploy/epaper.service.

Logging is deliberately near-silent. The frame is meant to run untouched for
months on an SD card, so a healthy loop writes nothing after startup: routine
events are debug, and each distinct fault is reported once rather than on every
cycle. An empty 'journalctl -u epaper' means it is working.
"""

import logging
import os
import shutil
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from pi import config, display

logger = logging.getLogger("epaper")

# Set when the process is asked to shut down. Every sleep in this module waits
# on it, so a systemd stop takes effect immediately instead of after a photo.
_stopping = threading.Event()

# Faults already written to the journal. A permanent fault - an unplugged panel,
# one corrupt bitmap, an empty photo folder - recurs on every cycle, so logging
# it each time would mean a traceback every few minutes for as long as the fault
# lasts. Each distinct fault is reported once and stays quiet until a clean pass
# clears the set.
_reported_faults = set()


def _handle_signal(signum, _frame):
    logger.debug("Received %s, shutting down", signal.Signals(signum).name)
    _stopping.set()


def _sleep(seconds):
    """Sleep, but wake immediately if the process has been asked to stop."""
    _stopping.wait(seconds)


def _report_fault(signature, message, *args, show_traceback=False):
    """
    Write a fault to the journal, but only the first time it is seen.

    Parameters:
        signature (tuple): Identity of the fault. Display failures deliberately
            leave the photo name out of it, so a dead panel reports once instead
            of once per photo in the folder.
        message (str): Log message, %-style, with args following.
        show_traceback (bool): Log the current exception's traceback too.

    Returns:
        None
    """
    if signature in _reported_faults:
        return

    _reported_faults.add(signature)
    if show_traceback:
        logger.exception(message, *args)
    else:
        logger.warning(message, *args)


def _clear_faults():
    """Note that a full pass succeeded, logging the recovery at most once."""
    if _reported_faults:
        _reported_faults.clear()
        logger.info("Recovered, displaying photos normally")


def mirror_incoming_to_display():
    """
    Make the display folder match the incoming folder, and return what to show.

    Only .bmp files are considered. Files that were modified very recently are
    skipped, so a photo still being transferred is not copied mid-write, and
    each copy lands via a temporary name so the display folder never contains a
    half-written file either.

    Returns:
        list[Path]: Sorted paths of the bitmaps that are ready to display.
    """
    config.INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    config.DISPLAY_DIR.mkdir(parents=True, exist_ok=True)

    now = time.time()

    # Two sets, and the difference between them matters. 'present' is every
    # photo that exists at all; 'settled' is the subset that has finished
    # transferring. Deletions are decided against 'present', because a photo
    # still being written has not gone away - deciding against 'settled' blanks
    # the whole frame every time a batch of photos starts arriving.
    present = set()
    settled = {}
    for path in config.INCOMING_DIR.iterdir():
        if not path.is_file() or path.suffix.lower() != ".bmp":
            continue
        present.add(path.name)

        # A negative age means the file is stamped in the future, which happens
        # on a Pi Zero because it has no real time clock: until NTP syncs, the
        # clock reads whatever it was at last shutdown. Treat those as settled,
        # otherwise a skewed clock hides every photo indefinitely.
        age = now - path.stat().st_mtime
        if age >= config.STABLE_SECONDS or age < 0:
            settled[path.name] = path
        else:
            logger.debug("Skipping %s, still being written", path.name)

    existing = {
        path.name: path
        for path in config.DISPLAY_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".bmp"
    }

    for name in sorted(existing.keys() - present):
        existing[name].unlink(missing_ok=True)
        logger.info("Removed %s, no longer in the incoming folder", name)

    for name, source in sorted(settled.items()):
        destination = config.DISPLAY_DIR / name

        # Compare modification time, not size. Every bitmap for this panel is
        # 600x448 in palette mode and therefore exactly the same number of
        # bytes, so a size check would never notice a photo swapped in under an
        # existing name. copy2 below preserves mtime, which makes this work.
        if name in existing:
            source_stat, existing_stat = source.stat(), existing[name].stat()
            if int(source_stat.st_mtime) <= int(existing_stat.st_mtime):
                continue

        temporary = destination.with_suffix(destination.suffix + ".part")
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
        logger.info("%s %s", "Replaced" if name in existing else "Added", name)

    return sorted(
        path
        for path in config.DISPLAY_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".bmp"
    )


def is_quiet_hour(now=None):
    """
    Say whether the panel should be holding still right now.

    Uses the Pi's local time, so the timezone is set once with
    'timedatectl set-timezone' rather than being calculated here. That is what
    makes this correct across daylight saving, which hand-rolled UTC offset
    arithmetic never is.

    Parameters:
        now (datetime): Defaults to the current local time.

    Returns:
        bool: True if the current hour falls inside the configured quiet hours.
    """
    hour = (now or datetime.now()).hour
    start, end = config.PAUSE_FROM_HOUR, config.PAUSE_UNTIL_HOUR

    if start == end:
        return False
    if start < end:
        return start <= hour < end
    # Range wraps past midnight, e.g. 22:00 through 06:00.
    return hour >= start or hour < end


def wait_out_quiet_hours():
    """Block until the quiet period is over, or until the process is stopping."""
    announced = False
    while is_quiet_hour() and not _stopping.is_set():
        if not announced:
            logger.debug("Quiet hours, holding the current image")
            announced = True
        _sleep(config.PAUSE_POLL_SECONDS)


def run():
    """Run the display loop until the process is asked to stop."""
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("EPAPER_DEBUG") else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        stream=sys.stdout,
    )

    try:
        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)
    except ValueError:
        # Signals can only be hooked from the main thread. Under systemd this
        # always is the main thread; this guard keeps the loop runnable from a
        # thread in tests, where the stop event is set directly instead.
        logger.debug("Not the main thread, skipping signal handler setup")

    logger.info("Starting up as %s, reading photos from %s",
                config.FRAME_NAME, config.INCOMING_DIR)

    while not _stopping.is_set():
        try:
            photos = mirror_incoming_to_display()

            if not photos:
                _report_fault(("empty",), "No photos to display, waiting")
                _sleep(config.ERROR_RETRY_SECONDS)
                continue

            # Only a pass that shows every photo without complaint counts as
            # healthy. Clearing after each individual success instead would let
            # one permanently broken photo re-report itself every rotation.
            clean_pass = True

            for photo in photos:
                if _stopping.is_set():
                    break

                wait_out_quiet_hours()
                if _stopping.is_set():
                    break

                try:
                    display.show(photo)
                except FileNotFoundError:
                    # Removed by a mirror pass on another cycle. Skip it.
                    logger.debug("%s disappeared before it could be shown", photo.name)
                    continue
                except Exception as error:
                    # One unreadable photo must not take down the whole frame.
                    clean_pass = False
                    _report_fault(
                        ("display", type(error).__name__, str(error)),
                        "Could not display %s: %s", photo.name, error,
                        show_traceback=True,
                    )

                _sleep(config.DISPLAY_SECONDS)

            if clean_pass and not _stopping.is_set():
                _clear_faults()

        except Exception as error:
            _report_fault(
                ("loop", type(error).__name__, str(error)),
                "Display loop error: %s", error,
                show_traceback=True,
            )
            _sleep(config.ERROR_RETRY_SECONDS)

    display.sleep()
    logger.debug("Stopped")


if __name__ == "__main__":
    run()
