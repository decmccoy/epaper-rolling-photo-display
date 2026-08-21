"""Prepare an album of photos and send the results to every frame.

    python -m sender.load_photos --zip "C:\\path\\to\\album.zip"
    python -m sender.load_photos --zip "album.zip" --target living-room

Photos are converted once and then sent to each frame in turn, since every frame
uses the same panel. Run with --no-send to convert only, which is the quickest
way to eyeball the dithered bitmaps before anything touches a frame.
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

from sender import conversion, transfer

logger = logging.getLogger("sender")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKING = REPO_ROOT / "working"


DEFAULT_CONFIG = REPO_ROOT / "frames.json"

PANEL_WIDTH = 600
PANEL_HEIGHT = 448


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert an album of photos to e-paper bitmaps and send them to the Pi.",
    )
    parser.add_argument(
        "--zip", dest="zip_path", type=Path, required=True,
        help="Zip file of photos, as exported from Google Photos or similar.",
    )
    parser.add_argument(
        "--album", default=None,
        help="Subfolder inside the zip to use. Omit to use everything in it.",
    )
    parser.add_argument(
        "--config", dest="config_path", type=Path, default=DEFAULT_CONFIG,
        help=f"Frame connection settings. Default: {DEFAULT_CONFIG.name}",
    )
    parser.add_argument(
        "--target", dest="targets", action="append", metavar="NAME",
        help="Frame to send to, by its name in the config file. Repeatable. "
             "Omit, or pass 'all', to send to every frame in the file.",
    )
    parser.add_argument(
        "--working", dest="working_dir", type=Path, default=DEFAULT_WORKING,
        help=f"Scratch directory for intermediate files. Default: {DEFAULT_WORKING.name}",
    )
    parser.add_argument(
        "--no-send", action="store_true",
        help="Convert only, do not connect to the Pi.",
    )
    parser.add_argument(
        "--keep-working", action="store_true",
        help="Leave the scratch directory in place for inspection.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Log every file, not just a summary per photo.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-8s %(message)s",
        stream=sys.stdout,
    )

    if not args.zip_path.exists():
        logger.error("No zip file at %s", args.zip_path)
        return 1

    # Read the config before doing any slow work, so a typo in a hostname or an
    # unknown --target fails in a second rather than after converting two
    # hundred photos.
    targets = {}
    if not args.no_send:
        try:
            targets = transfer.read_targets(args.config_path, args.targets)
        except (FileNotFoundError, ValueError) as error:
            logger.error("%s", error)
            return 1
        logger.info("Sending to %d frame(s): %s", len(targets), ", ".join(targets))

    working_dir = args.working_dir
    if working_dir.exists():
        # Left over from an interrupted run. Starting clean is what stops the
        # old script from silently sending last month's photos again.
        logger.info("Clearing previous working directory %s", working_dir)
        shutil.rmtree(working_dir)

    try:
        unzipped = conversion.unzip_album(args.zip_path, working_dir / "unzipped")
        source = unzipped / args.album if args.album else unzipped
        if not source.exists():
            logger.error("No folder named '%s' inside the zip", args.album)
            return 1

        bitmap_dir = conversion.prepare_album(
            source, working_dir, PANEL_WIDTH, PANEL_HEIGHT
        )

        bitmaps = sorted(bitmap_dir.glob("*.bmp"))
        logger.info("Prepared %d bitmaps in %s", len(bitmaps), bitmap_dir)

        if args.no_send:
            logger.info("--no-send given, stopping before transfer")
            return 0

        results = []
        for name, settings in targets.items():
            # Must match EPAPER_INCOMING on the frame (see pi/config.py). Photos
            # live outside the git checkout so a deploy cannot delete them.
            remote_dir = settings.get(
                "remote_photos_path", f"/home/{settings['username']}/epaper-data/photos"
            )

            try:
                client = transfer.connect(settings)
                try:
                    uploaded, deleted, unchanged = transfer.mirror_to_pi(
                        client, bitmap_dir, remote_dir
                    )
                finally:
                    client.close()
            except Exception as error:
                # Deliberately broad: a frame that is unplugged, asleep or on a
                # different network must not stop the others getting photos.
                # Every failure is reported and turns into a non-zero exit below.
                logger.error("%s: %s", name, error)
                results.append((name, False, f"FAILED - {error}"))
                continue

            results.append((name, True, (
                f"{uploaded} uploaded, {deleted} deleted, "
                f"{unchanged} already up to date"
            )))

        logger.info("Done.")
        label_width = max((len(name) for name, _, _ in results), default=0) + 1
        for name, _, summary in results:
            logger.info("  %-*s %s", label_width, f"{name}:", summary)

        return 0 if all(ok for _, ok, _ in results) else 1

    finally:
        if args.keep_working:
            logger.info("Working files left in %s", working_dir)
        elif working_dir.exists():
            shutil.rmtree(working_dir)
            logger.info("Cleaned up %s", working_dir)


if __name__ == "__main__":
    raise SystemExit(main())
