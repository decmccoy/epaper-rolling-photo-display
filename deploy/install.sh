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
sudo apt install -y rsync python3-venv python3-pil python3-spidev python3-lgpio python3-gpiozero

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
# The upstream driver ships only a setup.py, so pip needs setuptools and wheel
# present to build it properly instead of falling back to "setup.py install".
"$REPO/.venv/bin/pip" install -q setuptools wheel

# --no-deps because the driver's setup.py picks its dependencies from a stale
# /sys/bus/platform/drivers/gpiomem-bcm2835 check that no longer matches this
# kernel, so it asks for Jetson.GPIO. epdconfig.py greps /proc/cpuinfo instead
# and correctly uses spidev + gpiozero, both of which come from apt above.
"$REPO/.venv/bin/pip" install -q --use-pep517 --no-build-isolation --no-deps "$HOME/e-Paper/RaspberryPi_JetsonNano/python"

if [ -s "$REPO/requirements-pi.txt" ]; then
    "$REPO/.venv/bin/pip" install -q -r "$REPO/requirements-pi.txt"
fi

echo "==> Allowing the deploy script to restart the service without a password"
echo "$SERVICE_USER ALL=(root) NOPASSWD: /bin/systemctl restart epaper" \
    | sudo tee /etc/sudoers.d/epaper > /dev/null
sudo chmod 0440 /etc/sudoers.d/epaper

echo "==> Making the deploy script executable"
chmod +x "$REPO"/deploy/*.sh 2>/dev/null || true

echo "==> Capping how much disk and memory the journal may use"
sudo mkdir -p /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/epaper.conf > /dev/null <<'EOF'
# Installed by epaper-rolling-photo-display/deploy/install.sh.
[Journal]
SystemMaxUse=32M
RuntimeMaxUse=16M
EOF
sudo systemctl restart systemd-journald

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
