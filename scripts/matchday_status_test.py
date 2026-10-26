"""Pure tests for matchday nudge window + combined notify titles."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import pandas as pd

from footymodel.live.fixture_health import STATE_FILE, record
from footymodel.live.matchday_status import (
    build_nudge_body,
    fixture_logged_on_sofascore,
    fixtures_in_lineup_nudge_window,
)
from notify_dashboard import build_notification

rec = {
    "fixture_id": "fpl_99",
    "home": "Arsenal",
    "away": "Chelsea",
    "kickoff": "2026-08-30T15:00:00+00:00",
}

now = pd.Timestamp("2026-08-30T13:30:00+00:00", tz="UTC")
payload = {"fixtures": [rec]}

STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
if STATE_FILE.exists():
    STATE_FILE.unlink()

pending = fixtures_in_lineup_nudge_window(now, payload)
assert len(pending) == 1, pending

record(
    "sofa_123",
    kickoff=rec["kickoff"],
    home="Arsenal",
    away="Chelsea",
    source="sofascore",
    outcome="processed",
)
assert fixture_logged_on_sofascore(rec)
assert fixtures_in_lineup_nudge_window(now, payload) == []

body = build_nudge_body([rec])
assert "matchday_laptop" in body
assert "Arsenal" in body

title, combined = build_notification(
    [{"fixture_id": "f1", "home": "A", "away": "B", "player": "Saka", "p_shots_gt0.5": "0.7"}],
    [{"home": "A", "away": "B", "model_p_over25": "0.55", "exp_total_goals": "2.8"}],
)
assert "props" in title and "goals" in title
assert "O2.5" in combined and "Saka" in combined

print("matchday_status_test: OK")
