#!/usr/bin/env bash
# Run SofaScore player props from a home network (Option A).
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi
python -m playwright install chromium
python -m footymodel.live.calendar --gate || true
python -m footymodel.live.sofascore_props_engine
echo "Done. If new rows were logged, commit data/processed/live_player_props.csv and push."
