<a id="readme-top"></a>

# Raspberry Pi Epaper Photo Frame

This project displays photos on an Epaper photo frame using a connected Raspberry Pi Zero.
This repo holds both the onboard software for the Pi and the script to convert photos on a
computer and send them to the Pi over the network.

Photos are converted on a computer and only finished bitmaps are sent to a frame.

## Table of Contents

- [Getting Started](#getting-started)
  - [Cloning](#cloning)
  - [File Structure](#file-structure)
  - [Setting up the Raspberry Pi](#setting-up-the-raspberry-pi)
  - [Connecting to the Pi](#connecting-to-the-pi)
  - [Installing the onboard software](#installing-the-onboard-software)
  - [Executing the script](#executing-the-script)
  - [Adding a wifi network to a running frame](#adding-a-wifi-network-to-a-running-frame)
- [Adding a frame](#adding-a-frame)
- [Deploying code changes](#deploying-code-changes)
- [Development](#development)
- [Authors](#authors)

## Getting Started

### Cloning

```bash
git clone https://github.com/decmccoy/epaper-rolling-photo-display.git
```

### File Structure

Onboard Pi files:

```text
├── pi/
│   ├── main_loop.py        # the display loop, started by systemd
│   ├── display.py          # Waveshare panel wrapper
│   └── config.py           # settings, all overridable by environment variable
├── deploy/
│   ├── install.sh          # one-time setup on a fresh image
│   ├── epaper.service      # runs the display loop
│   ├── epaper-update.*     # timer that pulls updates from GitHub
│   ├── pull-deploy.sh      # pulls from GitHub and restarts the frame
│   ├── render-units.sh     # fills this frame's user and path into the units
│   ├── epaper.env.example  # template for /etc/epaper/epaper.env
│   └── add-wifi.sh         # adds a wifi network to a running frame
└── requirements-pi.txt
```

The two `.service` files are templates, not finished units. They carry
`__EPAPER_USER__` and `__EPAPER_REPO__` placeholders that `render-units.sh` fills in with
this frame's real values before installing them to `/etc/systemd/system`.

Image transfer script files:

```text
├── sender/
│   ├── load_photos.py      # CLI entry point
│   ├── conversion.py       # HEIC/JPG/PNG -> 7-colour bitmap
│   └── transfer.py         # SFTP mirror to a frame
├── frames.json     # one entry per frame
└── requirements-sender.txt
```

### Setting up the Raspberry Pi

#### Dependencies

- [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
- An SSH client ([PuTTY](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) on
  Windows, or the built-in `ssh` command)
- [Bonjour Print Services](https://support.apple.com/kb/DL999), if you are on Windows and want
  to reach the Pi by its `.local` name

#### Imaging the micro SD card

- Plug the card into a computer, open the imager and select **Raspberry Pi OS Lite (32-bit)**, under `Raspberry Pi OS (other)`

    > ⚠️ The Pi Zero W is ARMv6 and the 64-bit images will not boot. Lite rather than Desktop, because there is no monitor and only 512&nbsp;MB of RAM.

- Set the hostname, and the username and password
    > ⚠️ Don't forget these values
- Enter the wifi credentials
- Set the locale and timezone
- Enable SSH

    > Public-key authentication is recommended over a password. Generate a key first if you don't already have one, then paste the public half into the imager:
    >
    > ```bash
    > ssh-keygen -t ed25519 -C "epaper-frame"
    > ```

- Write this image to the card

#### Enabling USB gadget mode

Before ejecting the card, while the `bootfs` partition is still visible, enable USB gadget
mode. This gives you a shell over a plain USB cable even when the wifi settings are wrong,
which saves re-imaging the card.

- In `config.txt`, under `[all]`, add `dtoverlay=dwc2`
- In `cmdline.txt` insert `modules-load=dwc2,g_ether` immediately after `rootwait`
    > ⚠️ Ensure `cmdline.txt` stays one single line

#### First boot

Insert the micro SD into the Pi and plug it in. The first boot takes ten minutes so be patient.

### Connecting to the Pi

There are two ways in. The USB cable always works; wifi is more convenient once the Pi is on
the network.

#### Over a USB cable

Connect a cable from your computer to the Pi's `USB` port — **not** `PWR IN`. With gadget mode enabled the Pi appears as a network device:

```bash
ssh <username>@<hostname>.local
```

On Windows, `.local` names over this link are resolved by Bonjour, so install it if the
hostname is not found.

#### Over wifi

Once the Pi has joined your network you can reach it over wifi with the same command:

```bash
ssh <username>@<hostname>.local
```

### Adding a wifi network to a running frame

- Connect over usb cable or a network that it is already connected to
- Run:

```bash
~/epaper/deploy/add-wifi.sh "<SSID>"
```

It prompts for the password rather than taking it as an argument, so the password never
lands in `~/.bash_history` or in the process list. Set `WIFI_HIDDEN=1` for a network that
does not broadcast its SSID, or `WIFI_PRIORITY=<n>` to change which network wins when both
are in range (higher wins; the default is 10).

> The Zero W radio is 2.4&nbsp;GHz only, so the network has to broadcast a 2.4&nbsp;GHz band.

### Installing the onboard software

Once connected to the Pi:

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/decmccoy/epaper-rolling-photo-display.git ~/epaper
~/epaper/deploy/install.sh
```

> The Lite image does not ship `git`, so it has to be installed before the clone.

`install.sh` enables SPI, installs the apt packages, creates the virtualenv, fetches the
Waveshare driver, writes this frame's settings file, and renders and enables both systemd
units for the current user. It is safe to re-run.

Then review this frame's settings and restart to pick them up:

```bash
sudo nano /etc/epaper/epaper.env
sudo systemctl restart epaper
```

> A re-run of `install.sh` never overwrites an existing `/etc/epaper/epaper.env`

Check that the system is running:

```bash
systemctl status epaper
```

To turn on the debug pi logging:

```bash
sudo systemctl stop epaper
set -a; . /etc/epaper/epaper.env; set +a
EPAPER_DEBUG=1 ~/epaper/.venv/bin/python -m pi.main_loop
```

> Only systemd reads `/etc/epaper/epaper.env`, so a run started by hand would otherwise use
> the built-in defaults rather than this frame's settings — including a different photo
> folder. Sourcing it first is what makes the debug run match what the service does.
> `EPAPER_DEBUG=1` on the command line still wins over anything in the file.

### Executing the script

Install the desktop dependencies:

```bash
pip install -r requirements-sender.txt
```

- If necessary, create and fill out `frames.json` (see `EXAMPLE_frames.json` or below)
- Download all the photos as a zip file
- Run the following command in the base directory:

```bash
python -m sender.load_photos --zip "path/to/album.zip"
```

`frames.json` names each frame, and those names are what `--target` matches:

```json
{
  "targets": {
    "living-room": {
      "host_name": "frame-lounge.local",
      "username": "darcy",
      "key_filename": "~/.ssh/id_ed25519",
      "remote_photos_path": "/home/darcy/epaper-data/photos"
    },
    "parents": {
      "host_name": "frame-parents.local",
      "username": "mom_dad",
      "key_filename": "~/.ssh/id_ed25519",
      "remote_photos_path": "/home/mom_dad/epaper-data/photos"
    }
  }
}
```

`remote_photos_path` is that frame's `EPAPER_DATA` plus `/photos`.

| Flag | Effect |
| --- | --- |
| `--zip` | The exported album zip. Required. |
| `--album` | Subfolder inside the zip. Omit to use everything. |
| `--target` | Frame to send to, by name. Repeatable. Omit to send to all of them. |
| `--no-send` | Convert only. Use this to eyeball the bitmaps first. |
| `--force` | Re-upload every photo, not just the ones the frame is missing. |
| `--keep-working` | Leave the intermediate JPEGs in place for inspection. |
| `--config` | Point at a different settings file. |
| `--verbose` | Log every file, not just a summary per photo. |

Photos are converted once and then sent to each frame in turn. To load one frame only:

```bash
python -m sender.load_photos --zip "path/to/album.zip" --target living-room
```

> Each frame is reported separately and the command exits non-zero if any of them failed.

Photos are matched by filename. A bitmap whose name the frame already has is left alone,
and a name the album no longer contains is deleted from the frame.

> The one thing this cannot see is a photo whose **content** changed while its **name** stayed
> the same. That is rare for photos, but it is guaranteed after any edit to `conversion.py`. Send with `--force` to send all the photos:
>
> ```bash
> python -m sender.load_photos --zip "path/to/album.zip" --force
> ```

## Adding a frame

- Follow the steps above except with its own hostname, username and wifi. You can use the same public key
- Add another entry to `frames.json` on the computer, with its hostname, username and `remote_photos_path`
- To send it photos on its own, use:

    ```bash
    python -m sender.load_photos --zip "path/to/album.zip" --target <name>
    ```

## Deploying code changes

Each frame checks GitHub every hour and restarts itself if anything changed.

To force an immediate update, or to check on it:

```bash
sudo systemctl start epaper-update.service
journalctl -u epaper-update -n 20
```

The hourly deploy updates code only. A change to the systemd units themselves is not picked up. After changing a
unit, install it by hand on each frame:

```bash
~/epaper/deploy/render-units.sh
sudo systemctl restart epaper
```

## Development

The display loop runs on a normal computer without a panel attached:

```bash
EPAPER_DRY_RUN=1 EPAPER_DISPLAY_SECONDS=2 python -m pi.main_loop
```

Every setting in `pi/config.py` has an environment variable override, listed in that file.
On a real frame the ones that vary per device are set in `/etc/epaper/epaper.env`; the rest
keep their defaults. Photos and display state live in `~/epaper-data`, deliberately outside
the git working tree so that a deploy's `git reset --hard` can never delete them.

The sender converts without touching a frame, which is the quickest way to check a
conversion change:

```bash
python -m sender.load_photos --zip "path/to/album.zip" --no-send --keep-working
```

## Authors

- [decmccoy](https://github.com/decmccoy)
- [darcymccoy](https://github.com/darcymccoy)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
