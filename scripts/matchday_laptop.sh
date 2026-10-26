#!/usr/bin/env bash
# Laptop match-day helper: goals O/U + player props (one SofaScore session).
#
# Usage:
#   ./scripts/matchday_laptop.sh show              # upcoming kickoffs + when to poll
#   ./scripts/matchday_laptop.sh once              # poll only if calendar gate is open
#   ./scripts/matchday_laptop.sh loop [seconds]    # repeat until Ctrl+C (default 1200s)
#   ./scripts/matchday_laptop.sh loop 900 --push   # also git commit+push new props rows
#
# Requires: home Wi‑Fi (SofaScore blocks datacenter IPs). Keep laptop awake on matchdays.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

INTERVAL=1200
PUSH=false

if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

usage() {
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

setup_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found" >&2
    exit 1
  fi
  python3 -m playwright install chromium >/dev/null 2>&1 || python3 -m playwright install chromium
}

gate_should_run() {
  local out line val
  out="$(python3 -m footymodel.live.calendar --gate 2>&1)" || true
  printf '%s\n' "$out"
  line="$(printf '%s\n' "$out" | grep -E 'should_run=(True|False|true|false)' | tail -1 || true)"
  val="$(echo "${line#should_run=}" | tr '[:upper:]' '[:lower:]')"
  [[ "$val" == "true" ]]
}

run_matchday_poll() {
  python3 -m footymodel.live.sofascore_matchday
}

maybe_push() {
  if [[ "$PUSH" != "true" ]]; then
    echo "Tip: pass --push to commit and push data/processed/* to update the dashboard."
    return 0
  fi
  git config user.name >/dev/null 2>&1 || git config user.name "footymodel laptop"
  git config user.email >/dev/null 2>&1 || git config user.email "footymodel@local"
  local changed=false
  for f in data/processed/live_player_props.csv \
           data/processed/match_detail.jsonl \
           data/processed/sofascore_props_seen_fixtures.json \
           data/processed/live_fixture_health.json \
           data/processed/live_recommendations.csv \
           data/processed/sofascore_seen_fixtures.json \
           data/processed/paper_props_bankroll.json \
           data/processed/paper_bankroll_bets.csv \
           data/processed/paper_props_bets.csv; do
    [[ -f "$f" ]] && git add "$f" && changed=true
  done
  if [[ "$changed" != "true" ]]; then
    echo "No processed props files to push."
    return 0
  fi
  if git diff --cached --quiet; then
    echo "No new props rows to commit."
    return 0
  fi
  git commit -m "laptop props: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  git push
  if [[ -n "${NOTIFY_SECRET:-}" ]]; then
    python3 scripts/notify_dashboard.py || true
  fi
  echo "Pushed — Vercel dashboard will refresh on next deploy/data read."
}

cmd="${1:-show}"
shift || true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push) PUSH=true ;;
    -h|--help) usage 0 ;;
    *)
      if [[ "$cmd" == "loop" && "$INTERVAL" == "1200" && "$1" =~ ^[0-9]+$ ]]; then
        INTERVAL="$1"
      else
        echo "Unknown argument: $1" >&2
        usage 1
      fi
      ;;
  esac
  shift
done

setup_python

case "$cmd" in
  show)
    python3 scripts/matchday_schedule.py
    echo ""
    echo "Commands:"
    echo "  ./scripts/matchday_laptop.sh once          # single gated poll"
    echo "  ./scripts/matchday_laptop.sh loop          # every ${INTERVAL}s while you keep this open"
    echo "  ./scripts/matchday_laptop.sh loop 900 --push"
    ;;
  once)
    if gate_should_run; then
      echo "Gate open — running SofaScore matchday (goals O/U + props)..."
      run_matchday_poll
      maybe_push
    else
      echo "Gate closed — no fixture in the live window (or all seen). Nothing to do."
      exit 0
    fi
    ;;
  loop)
    echo "Match-day loop every ${INTERVAL}s (Ctrl+C to stop). Use home Wi‑Fi; keep laptop awake."
    while true; do
      echo ""
      echo "=== $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="
      if gate_should_run; then
        run_matchday_poll || echo "! matchday poll failed (network or SofaScore) — will retry."
        maybe_push
      else
        echo "Gate closed — sleeping ${INTERVAL}s."
      fi
      sleep "$INTERVAL"
    done
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage 1
    ;;
esac
