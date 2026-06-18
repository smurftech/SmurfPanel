#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$HOME/.local/opt/pcpanel-gui"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

if [[ ! -x "$ROOT_DIR/dist/pcpanel-gui/pcpanel-gui" ]]; then
  echo "Build not found: $ROOT_DIR/dist/pcpanel-gui/pcpanel-gui" >&2
  echo "Run: .venv/bin/python -m PyInstaller pcpanel-gui.spec --clean --noconfirm" >&2
  exit 1
fi

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
rm -rf "$APP_DIR"
cp -a "$ROOT_DIR/dist/pcpanel-gui" "$APP_DIR"
ln -sfn "$APP_DIR/pcpanel-gui" "$BIN_DIR/pcpanel-gui"
cp "$ROOT_DIR/pcpanel/assets/pcpanel.svg" "$ICON_DIR/pcpanel.svg"
sed "s#__EXEC_PATH__#$APP_DIR/pcpanel-gui#g" \
  "$ROOT_DIR/packaging/pcpanel-gui.desktop" > "$DESKTOP_DIR/pcpanel-gui.desktop"
chmod +x "$DESKTOP_DIR/pcpanel-gui.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Installed PCPanel GUI:"
echo "  App: $APP_DIR/pcpanel-gui"
echo "  Launcher: $DESKTOP_DIR/pcpanel-gui.desktop"
echo "  Command: pcpanel-gui"
