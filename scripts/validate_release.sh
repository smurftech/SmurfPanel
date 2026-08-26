#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PCPANEL_PYTHON:-$ROOT_DIR/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment not found: $PYTHON_BIN" >&2
  echo "Set PCPANEL_PYTHON to the project Python interpreter." >&2
  exit 1
fi

cd "$ROOT_DIR"
"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" -m json.tool config.example.json >/dev/null
"$PYTHON_BIN" -m compileall -q pcpanel
"$PYTHON_BIN" -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/pcpanel-release-wheel .

if [[ "${1:-}" == "--build" ]]; then
  if ! command -v objdump >/dev/null 2>&1; then
    echo "Standalone build requires objdump (usually provided by binutils)." >&2
    exit 1
  fi
  "$PYTHON_BIN" -m PyInstaller pcpanel-gui.spec --clean --noconfirm
  test -x "$ROOT_DIR/dist/pcpanel-gui/pcpanel-gui"
fi

echo "SmurfPanel release validation passed."
