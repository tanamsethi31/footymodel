#!/usr/bin/env bash
set -euo pipefail
cd /workspace

if ! python3 -m venv /tmp/venv-probe >/dev/null 2>&1; then
  rm -rf /tmp/venv-probe
  if command -v sudo >/dev/null; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv
  else
    echo "python3-venv is required but could not be installed" >&2
    exit 1
  fi
else
  rm -rf /tmp/venv-probe
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
PLAYWRIGHT_PY="$(command -v python)"
python -m playwright install chromium
if command -v sudo >/dev/null; then
  sudo env PATH="$PATH" "$PLAYWRIGHT_PY" -m playwright install-deps chromium
else
  python -m playwright install-deps chromium
fi

cd /workspace/dashboard
npm ci
