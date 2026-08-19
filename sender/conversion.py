"""Turn an album of ordinary photos into bitmaps the ACeP panel can render.

All of this runs on your computer, never on the Pi. Decoding HEIC and dithering
to a 7-colour palette takes seconds here and a very long time on an ARMv6 Zero W,
so the Pi only ever receives finished bitmaps.
"""

import logging
import zipfile
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

logger = logging.getLogger(__name__)

# Lets Pillow open the HEIC files that iPhones produce.
register_heif_opener()

ACCEPTED_IMAGE_TYPES = (".heic", ".heif", ".jpg", ".jpeg", ".png")

# The seven colours the Waveshare 5.65in ACeP panel can actually produce.
PANEL_PALETTE = [
    0, 0, 0,          # black
    255, 255, 255,    # white
    255, 0, 0,        # red
    0, 255, 0,        # green
    0, 0, 255,        # blue
    255, 255, 0,      # yellow
    255, 128, 0,      # orange
]


def unzip_album(zip_path, extract_to):
    """
    Unzip an exported album.

    Parameters:
        zip_path (Path): The zip file to extract.
        extract_to (Path): Directory to extract into. Created if missing.

    Returns:
        Path: The directory the contents were extracted to.
    """
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_to)

    logger.info("Extracted %s to %s", Path(zip_path).name, extract_to)
    return extract_to


def find_photos(source_dir):
    """
    Collect every usable image in a directory tree.

    Parameters:
        source_dir (Path): Directory to search, recursively.

    Returns:
        list[Path]: Sorted paths of images with a supported extension.
    """
    return sorted(
        path
        for path in Path(source_dir).rglob("*")
        if path.is_file() and path.suffix.lower() in ACCEPTED_IMAGE_TYPES
    )


def convert_to_jpg(image_path, destination_folder):
    """
    Normalise any supported image to an upright RGB JPEG.

    Applies the EXIF orientation tag, without which photos taken in portrait on
    a phone arrive at the frame lying on their side.

    Parameters:
        image_path (Path): Source image.
        destination_folder (Path): Directory to write the JPEG into.

    Returns:
        Path: The path of the written JPEG.
    """
    destination_folder = Path(destination_folder)
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination = destination_folder / f"{Path(image_path).stem}.jpg"

    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image)
        image.convert("RGB").save(destination, "JPEG", quality=95)

    logger.debug("Converted %s", destination.name)
    return destination


def fit_to_panel(image_path, destination_folder, target_width, target_height):
    """
    Scale an image to fit the panel and pad it to exactly the panel's size.

    Aspect ratio is preserved and the leftover space is filled with white, which
    is the cheapest colour for the panel to render and reads as a photo border.

    Parameters:
        image_path (Path): Source JPEG.
        destination_folder (Path): Directory to write the result into.
        target_width (int): Panel width in pixels.
        target_height (int): Panel height in pixels.

    Returns:
        Path: The path of the written JPEG.
    """
    destination_folder = Path(destination_folder)
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination = destination_folder / f"{Path(image_path).stem}.jpg"

    with Image.open(image_path) as image:
        scale = min(target_width / image.width, target_height / image.height)
        new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        resized = image.resize(new_size, Image.Resampling.LANCZOS)

        padded = Image.new("RGB", (target_width, target_height), (255, 255, 255))
        padded.paste(
            resized,
            ((target_width - new_size[0]) // 2, (target_height - new_size[1]) // 2),
        )
        padded.save(destination, "JPEG", quality=95)

    logger.debug("Fitted %s to %dx%d", destination.name, target_width, target_height)
    return destination


def to_panel_bitmap(image_path, destination_folder):
    """
    Dither an image down to the panel's seven colours and save it as a bitmap.

    Parameters:
        image_path (Path): Source JPEG, already at panel size.
        destination_folder (Path): Directory to write the bitmap into.

    Returns:
        Path: The path of the written bitmap.
    """
    destination_folder = Path(destination_folder)
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination = destination_folder / f"{Path(image_path).stem}.bmp"

    # Pillow zero-fills the remaining palette entries, leaving seven distinct colours.
    palette_image = Image.new("P", (1, 1))
    palette_image.putpalette(PANEL_PALETTE)

    with Image.open(image_path) as image:
        bitmap = image.convert("RGB").quantize(
            palette=palette_image, dither=Image.Dither.FLOYDSTEINBERG
        )
        bitmap.save(destination)

    logger.debug("Wrote %s", destination.name)
    return destination


def prepare_album(source_dir, working_dir, panel_width, panel_height):
    """
    Run every photo in a directory through the full conversion pipeline.

    Intermediate stages are kept on disk so a bad conversion can be inspected
    rather than guessed at.

    Parameters:
        source_dir (Path): Directory of unzipped photos.
        working_dir (Path): Scratch directory for intermediate output.
        panel_width (int): Panel width in pixels.
        panel_height (int): Panel height in pixels.

    Returns:
        Path: Directory containing the finished bitmaps.
    """
    working_dir = Path(working_dir)
    jpg_dir = working_dir / "jpg"
    fitted_dir = working_dir / "fitted"
    bitmap_dir = working_dir / "bitmap"

    photos = find_photos(source_dir)
    if not photos:
        raise FileNotFoundError(
            f"No images with a supported extension found under {source_dir}. "
            f"Supported: {', '.join(ACCEPTED_IMAGE_TYPES)}"
        )

    logger.info("Preparing %d photos", len(photos))
    for index, photo in enumerate(photos, start=1):
        try:
            as_jpg = convert_to_jpg(photo, jpg_dir)
            fitted = fit_to_panel(as_jpg, fitted_dir, panel_width, panel_height)
            to_panel_bitmap(fitted, bitmap_dir)
            logger.info("[%d/%d] %s", index, len(photos), photo.name)
        except Exception as error:
            # One corrupt photo should not abandon the other ninety-nine.
            logger.warning("Skipped %s: %s", photo.name, error)

    return bitmap_dir
