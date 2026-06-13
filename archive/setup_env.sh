#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "This script must be sourced so the virtual environment stays active."
  echo "Use: source ./setup_env.sh"
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating virtual environment in .venv..."
  python3 -m venv .venv
fi

if [[ ! -f .venv/bin/activate ]]; then
  echo "Failed to create virtual environment."
  return 1
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements_venv.txt

echo "Virtual environment ready. Run: python3 web_pcpanel.py"
