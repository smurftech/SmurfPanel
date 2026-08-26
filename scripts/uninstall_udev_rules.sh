#!/usr/bin/env bash
set -euo pipefail

RULE_DESTINATION="/etc/udev/rules.d/99-pcpanel.rules"

if [[ -e "$RULE_DESTINATION" ]]; then
  sudo rm -f -- "$RULE_DESTINATION"
  sudo udevadm control --reload-rules
  sudo udevadm trigger --subsystem-match=usb --attr-match=idVendor=0483 --attr-match=idProduct=a3c4
  echo "Removed PCPanel Mini USB permissions from $RULE_DESTINATION"
else
  echo "PCPanel Mini udev rule is not installed."
fi
