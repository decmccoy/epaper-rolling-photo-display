#!/bin/bash
# One-time setup on a freshly imaged Pi. Run from the repo checkout:
#
#   git clone https://github.com/decmccoy/epaper-rolling-photo-display.git ~/epaper
#   ~/epaper/deploy/install.sh
#
# Safe to re-run.
set -euo pipefail

REPO="${EPAPER_REPO:-$HOME/epaper}"
DATA="${EPAPER_DATA:-$HOME/epaper-data}"
SERVICE_USER="$(id -un)"

echo "==> Installing apt packages (prebuilt for ARMv6, nothing compiles here)"
sudo apt update
sudo apt install -y git rsync python3-venv python3-pil python3-spidev python3-lgpio

echo "==> Enabling SPI"
sudo raspi-config nonint do_spi 0

echo "==> Creating data directories outside the git tree"
mkdir -p "$DATA/photos" "$DATA/display"

echo "==> Creating the virtualenv"
if [ ! -d "$REPO/.venv" ]; then
    python3 -m venv --system-site-packages "$REPO/.venv"
fi

echo "==> Installing the Waveshare panel driver"
if [ ! -d "$HOME/e-Paper" ]; then
    git clone --depth 1 https://github.com/waveshare/e-Paper.git "$HOME/e-Paper"
fi
"$REPO/.venv/bin/pip" install -q "$HOME/e-Paper/RaspberryPi_JetsonNano/python"

if [ -s "$REPO/requirements-pi.txt" ]; then
    "$REPO/.venv/bin/pip" install -q -r "$REPO/requirements-pi.txt"
fi

echo "==> Allowing the deploy hooks to restart the service without a password"
echo "$SERVICE_USER ALL=(root) NOPASSWD: /bin/systemctl restart epaper" \
    | sudo tee /etc/sudoers.d/epaper > /dev/null
sudo chmod 0440 /etc/sudoers.d/epaper

echo "==> Installing systemd units"
for unit in epaper.service epaper-update.service epaper-update.timer; do
    sed -e "s|/home/mom_dad/epaper|$REPO|g" \
        -e "s|^User=mom_dad$|User=$SERVICE_USER|" \
        "$REPO/deploy/$unit" | sudo tee "/etc/systemd/system/$unit" > /dev/null
done

sudo systemctl daemon-reload
sudo systemctl enable --now epaper.service
sudo systemctl enable --now epaper-update.timer

echo
echo "Done. Check it with:"
echo "  systemctl status epaper"
echo "  journalctl -u epaper -f"
echo
echo "Panel smoke test:"
echo "  $REPO/.venv/bin/python -c \"from waveshare_epd import epd5in65f; e=epd5in65f.EPD(); e.init(); e.Clear(); e.sleep(); print('panel OK')\""
