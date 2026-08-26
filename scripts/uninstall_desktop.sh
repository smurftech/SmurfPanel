#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/opt/pcpanel-gui"
BIN_LINK="$HOME/.local/bin/pcpanel-gui"
DESKTOP_FILE="$HOME/.local/share/applications/pcpanel-gui.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/scalable/apps/pcpanel.svg"

rm -rf "$APP_DIR"
rm -f "$BIN_LINK"
rm -f "$DESKTOP_FILE"
rm -f "$ICON_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Uninstalled SmurfPanel user app."
echo "Config was left untouched at: $HOME/.config/pcpanel/config.json"
