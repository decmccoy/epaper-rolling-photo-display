#!/bin/bash
# Add a wifi network to this frame and make it autoconnect.
#
#   ./deploy/add-wifi.sh "<SSID>" [connection-name]
#
# The password is read from a prompt rather than an argument, so it never lands
# in ~/.bash_history or in the process list.
set -euo pipefail

SSID="${1:?usage: add-wifi.sh <SSID> [connection-name]}"
NAME="${2:-$SSID}"
PRIORITY="${WIFI_PRIORITY:-10}"

read -rsp "Password for $SSID: " PSK
echo

sudo nmcli connection add type wifi con-name "$NAME" ifname wlan0 \
    ssid "$SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK"
sudo nmcli connection modify "$NAME" connection.autoconnect yes \
    connection.autoconnect-priority "$PRIORITY"

# Hidden networks need this or the Pi never probes for them.
if [ "${WIFI_HIDDEN:-0}" = "1" ]; then
    sudo nmcli connection modify "$NAME" 802-11-wireless.hidden yes
fi

nmcli connection show
echo
echo "The Zero W radio is 2.4GHz only. If it will not associate, check the band."
