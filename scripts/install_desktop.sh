#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/packaging" ]]; then
  ROOT_DIR="$SCRIPT_DIR"
else
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
if [[ -x "$ROOT_DIR/app/pcpanel-gui" ]]; then
  BUNDLE_DIR="$ROOT_DIR/app"
else
  BUNDLE_DIR="$ROOT_DIR/dist/pcpanel-gui"
fi

APP_DIR="$HOME/.local/opt/smurfpanel"
BIN_DIR="$HOME/.local/bin"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
DESKTOP_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
INSTALL_UDEV=false

for argument in "$@"; do
  case "$argument" in
    --with-udev) INSTALL_UDEV=true ;;
    --help|-h)
      echo "Usage: $0 [--with-udev]"
      echo "  --with-udev  Also install PCPanel Mini USB permissions (uses sudo)."
      exit 0
      ;;
    *)
      echo "Unknown option: $argument" >&2
      exit 2
      ;;
  esac
done

if [[ ! -x "$BUNDLE_DIR/pcpanel-gui" ]]; then
  echo "SmurfPanel application bundle not found: $BUNDLE_DIR/pcpanel-gui" >&2
  echo "Build it with: ./scripts/validate_release.sh --build" >&2
  exit 1
fi

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
rm -rf "$APP_DIR"
cp -a "$BUNDLE_DIR" "$APP_DIR"
ln -sfn "$APP_DIR/pcpanel-gui" "$BIN_DIR/smurfpanel"
ln -sfn "$APP_DIR/pcpanel-gui" "$BIN_DIR/smurfpanel-gui"
ln -sfn "$APP_DIR/pcpanel-gui" "$BIN_DIR/pcpanel-gui"
cp "$ROOT_DIR/pcpanel/assets/pcpanel.svg" "$ICON_DIR/smurfpanel.svg"
sed "s#__EXEC_PATH__#$APP_DIR/pcpanel-gui#g" \
  "$ROOT_DIR/packaging/pcpanel-gui.desktop" > "$DESKTOP_DIR/smurfpanel.desktop"
chmod +x "$DESKTOP_DIR/smurfpanel.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi

if [[ "$INSTALL_UDEV" == true ]]; then
  "$ROOT_DIR/scripts/install_udev_rules.sh"
fi

echo "Installed SmurfPanel:"
echo "  App: $APP_DIR/pcpanel-gui"
echo "  Launcher: $DESKTOP_DIR/smurfpanel.desktop"
echo "  Commands: smurfpanel, smurfpanel-gui, pcpanel-gui"
echo "  Launch now: $BIN_DIR/smurfpanel"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo
    echo "Note: $BIN_DIR is not currently in PATH."
    echo "For this terminal, run:"
    echo "  export PATH=\"$BIN_DIR:\$PATH\""
    echo "To keep it available, add that line to your shell profile and open a new terminal."
    ;;
esac

if [[ "$INSTALL_UDEV" == false ]]; then
  echo "PCPanel Mini permissions were not changed."
  echo "Run '$ROOT_DIR/scripts/install_udev_rules.sh' if the device cannot connect."
fi
