"""Turn an album of ordinary photos into bitmaps the ACeP panel can render.

All of this runs on your computer, never on the Pi. Decoding HEIC and dithering
to a 7-colour palette takes seconds here and a very long time on an ARMv6 Zero W,
so the Pi only ever receives finished bitmaps.
"""

import json
import logging
import os
import time
import zipfile
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageOps, ImageFont
from pillow_heif import register_heif_opener

logger = logging.getLogger(__name__)

# Lets Pillow open the HEIC files that iPhones produce.
register_heif_opener()

ACCEPTED_IMAGE_TYPES = (".heic", ".heif", ".jpg", ".jpeg", ".png")

FONT_SIZE = 20
FONT = font = ImageFont.truetype("arial.ttf", FONT_SIZE)


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


def extract_photo_date(image_path):
    """
    Extract the date/time from EXIF metadata.

    Tries DateTimeOriginal (photo taken), then DateTimeDigitized, then DateTime.
    Returns a formatted date string or None if not found.

    Parameters:
        image_path (Path): Source image file.

    Returns:
        str: Formatted date string like "NOV 2023" or None if not available.
    """
    try:
        with Image.open(image_path) as image:
            exif = image.getexif()
            if not exif:
                return None

            # Try different EXIF date fields in order of preference
            date_str = (
                exif.get(36867)  # DateTimeOriginal (when photo was taken)
                or exif.get(36868)  # DateTimeDigitized
                or exif.get(306)  # DateTime
            )

            if date_str:
                # Parse "YYYY:MM:DD HH:MM:SS" format
                dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                # Return formatted as "MON YYYY"
                return dt.strftime("%b %Y").upper()
    except Exception as error:
        logger.debug("Could not extract date from %s: %s", Path(image_path).name, error)

    return None


def save_photo_metadata(image_path, metadata_path, metadata):
    """
    Save photo metadata to a JSON sidecar file.

    Parameters:
        image_path (Path): The photo file (used for the stem).
        metadata_path (Path): Directory to save the metadata JSON into.
        metadata (dict): Metadata dictionary to save.
    """
    metadata_path = Path(metadata_path)
    metadata_path.mkdir(parents=True, exist_ok=True)
    sidecar = metadata_path / f"{Path(image_path).stem}.json"

    with open(sidecar, "w") as f:
        json.dump(metadata, f)


def load_photo_metadata(image_path, metadata_path):
    """
    Load photo metadata from a JSON sidecar file.

    Parameters:
        image_path (Path): The photo file (used for the stem).
        metadata_path (Path): Directory where metadata JSON files are stored.

    Returns:
        dict: Metadata dictionary or empty dict if not found.
    """
    sidecar = Path(metadata_path) / f"{Path(image_path).stem}.json"
    if sidecar.exists():
        try:
            with open(sidecar, "r") as f:
                return json.load(f)
        except Exception as error:
            logger.warning("Could not load metadata from %s: %s", sidecar.name, error)

    return {}


def convert_to_jpg(image_path, destination_folder, metadata_folder=None):
    """
    Normalise any supported image to an upright RGB JPEG.

    Applies the EXIF orientation tag, without which photos taken in portrait on
    a phone arrive at the frame lying on their side.

    Extracts and saves photo metadata (date taken) to a JSON sidecar file for
    later retrieval when adding date stamps.

    Parameters:
        image_path (Path): Source image.
        destination_folder (Path): Directory to write the JPEG into.
        metadata_folder (Path): Directory to write metadata JSON into. If None, metadata is not saved.

    Returns:
        Path: The path of the written JPEG.
    """
    destination_folder = Path(destination_folder)
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination = destination_folder / f"{Path(image_path).stem}.jpg"

    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image)
        image.convert("RGB").save(destination, "JPEG", quality=95)

    # Extract and save metadata
    if metadata_folder:
        photo_date = extract_photo_date(image_path)
        metadata = {"date": photo_date}
        save_photo_metadata(image_path, metadata_folder, metadata)

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

    # Ensure fresh bitmaps always have a current mtime so the display loop
    # recognizes them as newer than existing files with the same name.
    # This is essential when conversion.py changes (e.g., adding date stamps)
    # but filenames stay the same - without this, the Pi's mtime comparison
    # may skip copying updated bitmaps.
    now = time.time()
    os.utime(destination, (now, now))

    logger.debug("Wrote %s", destination.name)
    return destination

def add_date_stamp_to_jpeg(jpeg_path, destination_folder, date_stamp=None):
    """
    Add a date stamp to a JPEG image and save to destination folder.

    If no date_stamp is provided, displays "NO DATE" instead.
    The date stamp is added to the RGB image before dithering, resulting in
    better quality when converted to the panel's 7-colour palette.

    Parameters:
        jpeg_path (Path): Path to the JPEG image.
        destination_folder (Path): Directory to write the stamped JPEG into.
        date_stamp (str): The date stamp text to add. If None, uses "NO DATE".

    Returns:
        Path: The path of the written JPEG.
    """
    from PIL import ImageDraw

    destination_folder = Path(destination_folder)
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination = destination_folder / Path(jpeg_path).name

    

    with Image.open(jpeg_path) as image:
        draw = ImageDraw.Draw(image)
        if date_stamp is not None:
            left, top, right, bottom = draw.textbbox((0, 0), date_stamp, font=FONT)
            text_width = right - left
            text_height = bottom - top
            x = image.width - text_width - 5
            y = image.height - text_height - 6

            # White box behind the text
            draw.rectangle(
                [x - 6, y - 4, x + text_width + 6, y + text_height + 4],
                fill=(255, 255, 255),
            )

            # Black text on white box
            draw.text((x, y), date_stamp, font=FONT, fill=(0, 0, 0))

        image.save(destination, "JPEG", quality=95)

    logger.debug("Added date stamp to %s", destination.name)
    return destination


def prepare_album(source_dir, working_dir, panel_width, panel_height):
    """
    Run every photo in a directory through the full conversion pipeline.

    Intermediate stages are kept on disk so a bad conversion can be inspected
    rather than guessed at. Metadata (e.g., photograph date) is extracted from
    the original image's EXIF data and used for date stamps before dithering to
    the panel's 7-colour palette, resulting in better quality rendering.

    Parameters:
        source_dir (Path): Directory of unzipped photos.
        working_dir (Path): Scratch directory for intermediate output.
        panel_width (int): Panel width in pixels.
        panel_height (int): Panel height in pixels.

    Returns:
        Path: Directory containing the finished bitmaps with embedded date stamps.
    """
    working_dir = Path(working_dir)
    jpg_dir = working_dir / "jpg"
    fitted_dir = working_dir / "fitted"
    stamped_fitted_dir = working_dir / "fitted_stamped"
    bitmap_dir = working_dir / "bitmap"
    metadata_dir = working_dir / "metadata"

    photos = find_photos(source_dir)
    if not photos:
        raise FileNotFoundError(
            f"No images with a supported extension found under {source_dir}. "
            f"Supported: {', '.join(ACCEPTED_IMAGE_TYPES)}"
        )

    logger.info("Preparing %d photos", len(photos))
    for index, photo in enumerate(photos, start=1):
        try:
            as_jpg = convert_to_jpg(photo, jpg_dir, metadata_dir)
            fitted = fit_to_panel(as_jpg, fitted_dir, panel_width, panel_height)

            # Load the extracted metadata to get the date
            metadata = load_photo_metadata(photo, metadata_dir)
            date_stamp = metadata.get("date")

            # Add date stamp to JPEG before converting to bitmap for better quality
            stamped_fitted = add_date_stamp_to_jpeg(
                fitted, stamped_fitted_dir, date_stamp=date_stamp
            )

            # Convert the stamped JPEG to bitmap
            to_panel_bitmap(stamped_fitted, bitmap_dir)

            logger.info("[%d/%d] %s", index, len(photos), photo.name)
        except Exception as error:
            logger.warning("Skipped %s: %s", photo.name, error)

    return bitmap_dir
