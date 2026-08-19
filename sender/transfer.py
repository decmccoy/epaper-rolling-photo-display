"""Ship finished bitmaps to the Pi over SFTP.

This mirrors a local folder onto the Pi: files that are missing or a different
size are uploaded, files the Pi has but the album no longer contains are
deleted. Re-running after adding one photo therefore transfers one photo, not
the whole album, which matters on a Zero W's SD card.
"""

import json
import logging
import stat
from pathlib import Path

import paramiko

logger = logging.getLogger(__name__)


def read_pi_config(config_path):
    """
    Load the Pi connection settings.

    Expected keys: host_name, username, and then either key_filename (preferred)
    or password. Optional: port, remote_photos_path.

    Parameters:
        config_path (Path): Path to the JSON config file.

    Returns:
        dict: The parsed settings.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"No config at {config_path}. Copy EXAMPLE_raspberry_pi_info.json to "
            f"{config_path.name} and fill it in."
        )

    with config_path.open("r", encoding="utf-8") as config_file:
        settings = json.load(config_file)

    for required in ("host_name", "username"):
        if not settings.get(required):
            raise ValueError(f"'{required}' is missing from {config_path}")

    if not settings.get("key_filename") and not settings.get("password"):
        raise ValueError(
            f"{config_path} needs either 'key_filename' (preferred) or 'password'"
        )

    return settings


def connect(settings):
    """
    Open an SSH connection to the Pi.

    Prefers key authentication and falls back to a password only if no key is
    configured.

    Parameters:
        settings (dict): As returned by read_pi_config.

    Returns:
        paramiko.SSHClient: A connected client. The caller must close it.
    """
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    key_filename = settings.get("key_filename")
    client.connect(
        hostname=settings["host_name"],
        port=int(settings.get("port", 22)),
        username=settings["username"],
        key_filename=str(Path(key_filename).expanduser()) if key_filename else None,
        password=None if key_filename else settings.get("password"),
        timeout=30,
    )

    logger.info("Connected to %s", settings["host_name"])
    return client


def _ensure_remote_dir(sftp, remote_dir):
    """Create a remote directory and any missing parents."""
    built = ""
    for part in (segment for segment in str(remote_dir).split("/") if segment):
        built = f"{built}/{part}"
        try:
            sftp.stat(built)
        except IOError:
            sftp.mkdir(built)


def _put_atomically(sftp, local_path, remote_path):
    """Upload beside the target then rename, so a broken transfer leaves no half file."""
    temporary = f"{remote_path}.part"
    sftp.put(str(local_path), temporary)
    try:
        sftp.posix_rename(temporary, remote_path)
    except (IOError, AttributeError):
        # Server lacks the posix-rename extension; fall back to remove and rename.
        try:
            sftp.remove(remote_path)
        except IOError:
            pass
        sftp.rename(temporary, remote_path)


def mirror_to_pi(client, local_dir, remote_dir):
    """
    Make a folder on the Pi match a local folder of bitmaps.

    Parameters:
        client (paramiko.SSHClient): An already connected client.
        local_dir (Path): Folder of finished .bmp files.
        remote_dir (str): Destination folder on the Pi, as a POSIX path.

    Returns:
        tuple[int, int, int]: Counts of uploaded, deleted and unchanged files.
    """
    local_dir = Path(local_dir)
    local_files = {
        path.name: path
        for path in local_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".bmp"
    }

    sftp = client.open_sftp()
    try:
        _ensure_remote_dir(sftp, remote_dir)

        remote_files = {}
        for entry in sftp.listdir_attr(remote_dir):
            if not stat.S_ISDIR(entry.st_mode) and entry.filename.lower().endswith(".bmp"):
                remote_files[entry.filename] = (entry.st_size, int(entry.st_mtime))

        uploaded = deleted = unchanged = 0

        for name in sorted(set(remote_files) - set(local_files)):
            sftp.remove(f"{remote_dir}/{name}")
            logger.info("Deleted %s from the Pi", name)
            deleted += 1

        for name, path in sorted(local_files.items()):
            local_stat = path.stat()
            local_fingerprint = (local_stat.st_size, int(local_stat.st_mtime))

            # Modification time is part of the fingerprint because every bitmap
            # for this panel is exactly the same size, so size alone would never
            # detect a photo replaced under an existing name.
            if remote_files.get(name) == local_fingerprint:
                unchanged += 1
                continue

            remote_path = f"{remote_dir}/{name}"
            _put_atomically(sftp, path, remote_path)
            # Stamp the remote copy so the next run recognises it as unchanged.
            sftp.utime(remote_path, (int(local_stat.st_atime), int(local_stat.st_mtime)))
            logger.info("Uploaded %s", name)
            uploaded += 1

        return uploaded, deleted, unchanged
    finally:
        sftp.close()
