"""Ship finished bitmaps to a frame over SFTP.

This mirrors a local folder onto the frame: bitmaps whose names the frame does
not have are uploaded, names the album no longer contains are deleted.
Re-running after adding one photo therefore transfers one photo, not the whole
album, which matters on a Zero W's SD card.
"""

import json
import logging
import stat
from pathlib import Path

import paramiko

logger = logging.getLogger(__name__)


def _load_config_file(config_path):
    """Read and parse a config file, with a message that says what to copy."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"No config at {config_path}. Copy EXAMPLE_frames.json to "
            f"{config_path.name} and fill it in."
        )

    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def _validate_settings(settings, where):
    """
    Check one frame's settings for the keys a connection needs.

    Parameters:
        settings (dict): One frame's connection settings.
        where (str): How to describe the source in an error message.

    Returns:
        dict: The same settings, once they are known to be usable.
    """
    if not isinstance(settings, dict):
        raise ValueError(f"{where} is not a set of connection settings")

    for required in ("host_name", "username"):
        if not settings.get(required):
            raise ValueError(f"'{required}' is missing from {where}")

    if not settings.get("key_filename") and not settings.get("password"):
        raise ValueError(
            f"{where} needs either 'key_filename' (preferred) or 'password'"
        )

    return settings


def read_targets(config_path, wanted=None):
    """
    Load one or more frames from a config file.

    The file is a {"targets": {name: {...}}} object. Returns a dict of
    name -> settings, keyed by the names used by --target.

    Parameters:
        config_path (Path): Path to the JSON config file.
        wanted (list[str]): Names to select. None or ["all"] means every target.

    Returns:
        dict[str, dict]: Selected frames, keyed by name.
    """
    config_path = Path(config_path)
    config = _load_config_file(config_path)

    if not isinstance(config, dict):
        raise ValueError(f"{config_path} should contain a JSON object")

    targets = config.get("targets")
    if not isinstance(targets, dict) or not targets:
        raise ValueError(
            f"{config_path} has no frames in it. It needs a 'targets' object "
            f"with one entry per frame. See EXAMPLE_frames.json."
        )

    if wanted and "all" not in wanted:
        chosen = {}
        for name in wanted:
            if name not in targets:
                available = ", ".join(sorted(targets)) or "(none)"
                raise ValueError(
                    f"No frame named '{name}' in {config_path}. "
                    f"Frames in that file: {available}"
                )
            chosen[name] = targets[name]
        targets = chosen

    # Validate everything selected before any slow work starts, so a typo in one
    # frame's settings does not surface after the other frame is already loaded.
    return {
        name: _validate_settings(settings, f"frame '{name}' in {config_path}")
        for name, settings in targets.items()
    }


def connect(settings):
    """
    Open an SSH connection to the Pi.

    Prefers key authentication and falls back to a password only if no key is
    configured.

    Parameters:
        settings (dict): One frame's settings, as returned by read_targets.

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
    created = False
    built = ""
    for part in (segment for segment in str(remote_dir).split("/") if segment):
        built = f"{built}/{part}"
        try:
            sftp.stat(built)
        except IOError:
            sftp.mkdir(built)
            created = True

    # The frame reads EPAPER_DATA from /etc/epaper/epaper.env, which the sender
    # cannot see. If the photo folder was not already there, the frame is almost
    # certainly watching a different one and these uploads will go nowhere.
    if created:
        logger.warning(
            "Created %s - it did not exist. Check EPAPER_DATA in "
            "/etc/epaper/epaper.env on that frame matches this path.",
            remote_dir,
        )


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


def mirror_to_pi(client, local_dir, remote_dir, force=False):
    """
    Make a folder on the frame match a local folder of bitmaps.

    Bitmaps are matched by filename alone. The cost is that a photo replaced under a name the frame already has is not
    noticed. Pass force=True after changing anything in conversion.py, since
    that changes the content of every bitmap while leaving the names alone.

    Parameters:
        client (paramiko.SSHClient): An already connected client.
        local_dir (Path): Folder of finished .bmp files.
        remote_dir (str): Destination folder on the frame, as a POSIX path.
        force (bool): Re-upload every bitmap, even ones already there by name.

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

        remote_names = {
            entry.filename
            for entry in sftp.listdir_attr(remote_dir)
            if not stat.S_ISDIR(entry.st_mode)
            and entry.filename.lower().endswith(".bmp")
        }

        uploaded = deleted = unchanged = 0

        for name in sorted(remote_names - set(local_files)):
            sftp.remove(f"{remote_dir}/{name}")
            logger.info("Deleted %s from the frame", name)
            deleted += 1

        for name, path in sorted(local_files.items()):
            if name in remote_names and not force:
                unchanged += 1
                continue

            _put_atomically(sftp, path, f"{remote_dir}/{name}")
            logger.info("Uploaded %s", name)
            uploaded += 1

        return uploaded, deleted, unchanged
    finally:
        sftp.close()
