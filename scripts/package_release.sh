#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="$ROOT_DIR/dist/pcpanel-gui"
VERSION="$(sed -n 's/^version = "\([^"]*\)"/\1/p' "$ROOT_DIR/pyproject.toml" | head -n 1)"
ARCHITECTURE="$(uname -m)"
RELEASE_NAME="SmurfPanel-${VERSION}-linux-${ARCHITECTURE}"
STAGING_ROOT="$(mktemp -d)"
RELEASE_ROOT="$STAGING_ROOT/$RELEASE_NAME"
ARCHIVE="$ROOT_DIR/dist/$RELEASE_NAME.tar.gz"

cleanup() {
  rm -rf -- "$STAGING_ROOT"
}
trap cleanup EXIT

if [[ ! -x "$BUNDLE_DIR/pcpanel-gui" ]]; then
  echo "Standalone bundle not found: $BUNDLE_DIR/pcpanel-gui" >&2
  echo "Run: ./scripts/validate_release.sh --build" >&2
  exit 1
fi

mkdir -p "$RELEASE_ROOT/app" "$RELEASE_ROOT/packaging" \
  "$RELEASE_ROOT/pcpanel/assets" "$RELEASE_ROOT/scripts"
cp -a "$BUNDLE_DIR/." "$RELEASE_ROOT/app/"
cp "$ROOT_DIR/packaging/pcpanel-gui.desktop" "$RELEASE_ROOT/packaging/"
cp "$ROOT_DIR/packaging/99-pcpanel.rules" "$RELEASE_ROOT/packaging/"
cp "$ROOT_DIR/pcpanel/assets/pcpanel.svg" "$RELEASE_ROOT/pcpanel/assets/"
cp "$ROOT_DIR/scripts/install_desktop.sh" "$RELEASE_ROOT/install.sh"
cp "$ROOT_DIR/scripts/uninstall_desktop.sh" "$RELEASE_ROOT/uninstall.sh"
cp "$ROOT_DIR/scripts/install_udev_rules.sh" "$RELEASE_ROOT/scripts/"
cp "$ROOT_DIR/scripts/uninstall_udev_rules.sh" "$RELEASE_ROOT/scripts/"
cp "$ROOT_DIR/packaging/INSTALL.txt" "$RELEASE_ROOT/README.txt"
chmod +x "$RELEASE_ROOT/install.sh" "$RELEASE_ROOT/uninstall.sh" \
  "$RELEASE_ROOT/scripts/install_udev_rules.sh" \
  "$RELEASE_ROOT/scripts/uninstall_udev_rules.sh"

tar -C "$STAGING_ROOT" -czf "$ARCHIVE" "$RELEASE_NAME"
(
  cd "$ROOT_DIR/dist"
  sha256sum "$RELEASE_NAME.tar.gz" > "$RELEASE_NAME.tar.gz.sha256"
)

echo "Created SmurfPanel release:"
echo "  $ARCHIVE"
echo "  $ARCHIVE.sha256"
