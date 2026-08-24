#!/bin/bash
# Add a wifi network to this frame and make it autoconnect, or update the
# password of a network that is already configured.
#
#   ./deploy/add-wifi.sh "<SSID>" [connection-name]
#
# If a connection with the target name already exists it is overwritten in
# place rather than duplicated. NetworkManager does not enforce unique
# connection names, so adding a second profile under an existing name leaves
# two profiles fighting over which one autoconnects.
#
# The password is read from a prompt rather than an argument, so it never lands
# in ~/.bash_history.
set -euo pipefail

SSID="${1:?usage: add-wifi.sh <SSID> [connection-name]}"
NAME="${2:-$SSID}"
PRIORITY="${WIFI_PRIORITY:-10}"

# Duplicates left over from an earlier run would make "connection modify"
# ambiguous - it silently picks one of them - so refuse to guess.
MATCHES=$(nmcli -g NAME -e no connection show | grep -Fxc -- "$NAME" || true)
if [ "$MATCHES" -gt 1 ]; then
    echo "There are $MATCHES connections named '$NAME'." >&2
    echo "Delete the extras first, then re-run:" >&2
    echo "    sudo nmcli connection delete \"$NAME\"" >&2
    exit 1
fi

read -rsp "Password for $SSID: " PSK
echo

if [ "$MATCHES" -eq 1 ]; then
    # Note whether the frame is on this network right now, before we touch it.
    ACTIVE=$(nmcli -g NAME -e no connection show --active | grep -Fxc -- "$NAME" || true)
    echo "Updating existing connection '$NAME'."
    sudo nmcli connection modify "$NAME" \
        802-11-wireless.ssid "$SSID" \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK"
else
    ACTIVE=0
    sudo nmcli connection add type wifi con-name "$NAME" ifname wlan0 \
        ssid "$SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK"
fi

sudo nmcli connection modify "$NAME" connection.autoconnect yes \
    connection.autoconnect-priority "$PRIORITY"

# Hidden networks need this or the Pi never probes for them.
if [ "${WIFI_HIDDEN:-0}" = "1" ]; then
    sudo nmcli connection modify "$NAME" 802-11-wireless.hidden yes
fi

# A stored password only takes effect on the next activation, so if this is the
# network the frame is on right now, bounce it. If the new password is wrong
# this is where it fails - and on a headless frame that means no way back in.
if [ "$ACTIVE" -eq 1 ]; then
    echo "Reconnecting '$NAME' to apply the new password."
    sudo nmcli connection up "$NAME"
fi

nmcli connection show
echo
echo "The Zero W radio is 2.4GHz only. If it will not associate, check the band."
