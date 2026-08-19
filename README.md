<a id="readme-top"></a>

# Raspberry Pi Epaper Photo Frame

This project displays photos on an Epaper photo frame using a connected Raspberry Pi Zero.
This repo holds both the onboard software for the Pi and the script to convert photos on a
computer and send them to the Pi over the network.

Photos are converted on a computer and only finished bitmaps are sent to the Pi.

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
│   └── pull-deploy.sh      # pulls from GitHub and restarts the frame
└── requirements-pi.txt
```

Image transfer script files:

```text
├── sender/
│   ├── load_photos.py      # CLI entry point
│   ├── conversion.py       # HEIC/JPG/PNG -> 7-colour bitmap
│   └── transfer.py         # SFTP mirror to the Pi
├── EXAMPLE_raspberry_pi_info.json
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

    > ⚠️ 32-bit is not a preference. The Pi Zero W is ARMv6 and the 64-bit images will not boot.
    > Lite rather than Desktop, because there is no monitor and only 512&nbsp;MB of RAM.

- Set the hostname, and your own username and password
    > ⚠️ Don't forget these values
- Select `Configure wireless LAN` to enter your wifi credentials, and set the wifi country
- Set your locale and timezone
- Enable SSH

    > Public-key authentication is recommended over a password. Generate a key first if you don't already have one, then paste the public half into the imager:
    >
    > ```bash
    > ssh-keygen -t ed25519 -C "epaper-frame"
    > ```

- Then press `SAVE` and write the image to the card

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

Or, using PuTTY, enter the host name of the Pi and click `Open`:<br/>
![Putty Configuration](docs/assets/putty_configuration.png)<br/>

To add another wifi network, connect over the cable or the current network and run:

```bash
sudo nmcli connection add type wifi con-name <name> ifname wlan0 \
  ssid "<SSID>" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "<PASSWORD>"
sudo nmcli connection modify <name> connection.autoconnect yes \
  connection.autoconnect-priority 10
nmcli connection show
```

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
Waveshare driver, and enables both systemd units. It is safe to re-run.

Check that it worked and is running:

```bash
systemctl status epaper
journalctl -u epaper -f
```

To turn on the debug pi logging:

```bash
sudo systemctl stop epaper
EPAPER_DEBUG=1 ~/epaper/.venv/bin/python -m pi.main_loop
```

### Executing the script

Install the desktop dependencies:

```bash
pip install -r requirements-sender.txt
```

- Create and fill in the `raspberry_pi_info.json` config file
- Download all the photos as a zip file
- Run the following command in the base directory:

```bash
python -m sender.load_photos --zip "path/to/album.zip"
```

| Flag | Effect |
| --- | --- |
| `--zip` | The exported album zip. Required. |
| `--album` | Subfolder inside the zip. Omit to use everything. |
| `--no-send` | Convert only. Use this to eyeball the bitmaps first. |
| `--keep-working` | Leave the intermediate JPEGs in place for inspection. |
| `--config` | Point at a different settings file. |
| `--verbose` | Log every file, not just a summary per photo. |

Only changed photos are uploaded, and photos removed from the album are deleted from the Pi.

## Deploying code changes

The Pi checks GitHub every hour and restarts itself if anything changed.

To force an immediate update, or to check on it:

```bash
sudo systemctl start epaper-update.service
journalctl -u epaper-update -n 20
```

## Development

The display loop runs on a normal computer without a panel attached:

```bash
EPAPER_DRY_RUN=1 EPAPER_DISPLAY_SECONDS=2 python -m pi.main_loop
```

Every setting in `pi/config.py` has an environment variable override, listed in that file.
Photos and display state live in `~/epaper-data`, deliberately outside the git working tree
so that a deploy's `git reset --hard` can never delete them.

## Authors

- [decmccoy](https://github.com/decmccoy)
- [darcymccoy](https://github.com/darcymccoy)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
