#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULE_SOURCE="$ROOT_DIR/packaging/99-pcpanel.rules"
RULE_DESTINATION="/etc/udev/rules.d/99-pcpanel.rules"

if [[ ! -f "$RULE_SOURCE" ]]; then
  echo "Missing udev rule: $RULE_SOURCE" >&2
  exit 1
fi

sudo install -m 0644 "$RULE_SOURCE" "$RULE_DESTINATION"
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=usb --attr-match=idVendor=0483 --attr-match=idProduct=a3c4

echo "Installed PCPanel Mini USB permissions at $RULE_DESTINATION"
echo "Unplug and reconnect the PCPanel Mini before launching SmurfPanel."
