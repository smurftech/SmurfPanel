#!/usr/bin/env bash
set -euo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$HOME/.local/opt/smurfpanel"
LEGACY_APP_DIR="$HOME/.local/opt/pcpanel-gui"
DESKTOP_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
REMOVE_UDEV=false

for argument in "$@"; do
  case "$argument" in
    --remove-udev) REMOVE_UDEV=true ;;
    --help|-h)
      echo "Usage: $0 [--remove-udev]"
      echo "  --remove-udev  Also remove PCPanel Mini USB permissions (uses sudo)."
      exit 0
      ;;
    *)
      echo "Unknown option: $argument" >&2
      exit 2
      ;;
  esac
done

rm -rf "$APP_DIR"
rm -rf "$LEGACY_APP_DIR"
rm -f "$HOME/.local/bin/smurfpanel"
rm -f "$HOME/.local/bin/smurfpanel-gui"
rm -f "$HOME/.local/bin/pcpanel-gui"
rm -f "$DESKTOP_DIR/smurfpanel.desktop"
rm -f "$DESKTOP_DIR/pcpanel-gui.desktop"
rm -f "$ICON_DIR/smurfpanel.svg"
rm -f "$ICON_DIR/pcpanel.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi

if [[ "$REMOVE_UDEV" == true ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -x "$SCRIPT_DIR/scripts/uninstall_udev_rules.sh" ]]; then
    "$SCRIPT_DIR/scripts/uninstall_udev_rules.sh"
  else
    "$SCRIPT_DIR/uninstall_udev_rules.sh"
  fi
fi

echo "Uninstalled SmurfPanel user app."
echo "Config was left untouched at: $HOME/.config/pcpanel/config.json"
