"""Dry-run run_all.py's shared-fetch orchestration with a MOCKED API response
(no network, no quota spent). Validates the actual reason run_all.py exists:
ONE fixtures-by-date call and ONE lineups-per-fixture call feed BOTH the
goals and player-props engines, not two independent fetches each.

Uses tmp paths for the seen-fixtures/CSV state so this doesn't touch the
real project's live-polling files.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live import engine, run_all, shots_engine
from footymodel.live import namematch
from footymodel.players import load_players

tmp = Path(tempfile.mkdtemp())
engine.SEEN_FIXTURES_FILE = tmp / "seen.json"
engine.LIVE_LOG = tmp / "goals.csv"
run_all.LIVE_LOG = engine.LIVE_LOG
shots_engine.PROPS_LOG = tmp / "props.csv"
run_all.PROPS_LOG = shots_engine.PROPS_LOG

players = load_players()
home_us, away_us = "Manchester City", "Everton"
home_names = list(namematch.team_roster_index(players, "E0", home_us).keys())[:11]
away_names = list(namematch.team_roster_index(players, "E0", away_us).keys())[:11]

fixture = {
    "fixture": {"id": 999003,
               "date": (pd.Timestamp.now(tz="UTC") + pd.Timedelta(minutes=30)).isoformat()},
    "league": {"id": 39},  # E0
    "teams": {"home": {"id": 50, "name": home_us}, "away": {"id": 29, "name": away_us}},
}
mock_lineups = [
    {"team": {"id": 50, "name": home_us}, "startXI": [{"player": {"name": n}} for n in home_names]},
    {"team": {"id": 29, "name": away_us}, "startXI": [{"player": {"name": n}} for n in away_names]},
]
mock_odds = [{"bookmakers": [{"bets": [
    {"name": "Goals Over/Under",
     "values": [{"value": "Over 2.5", "odd": "1.9"}, {"value": "Under 2.5", "odd": "1.9"}]},
    {"name": "Home Player Shots",
     "values": [{"value": f"{home_names[0]} - 1+", "odd": "1.75"}]},
]}]}]

mock_client = MagicMock()
mock_client.fixtures_by_date.side_effect = lambda date_str: [fixture]
mock_client.lineups.return_value = mock_lineups
mock_client.odds.return_value = mock_odds

run_all.ApiFootballClient = lambda: mock_client

goal_rows, prop_rows = run_all.run_once()

print(f"fixtures_by_date calls: {mock_client.fixtures_by_date.call_count} (expect 2 — today+tomorrow)")
print(f"lineups calls: {mock_client.lineups.call_count} (expect 1 — SHARED across both engines)")
print(f"odds calls: {mock_client.odds.call_count} (expect 1 — SHARED across both engines)")
print(f"goal_rows: {len(goal_rows)} (expect 1)")
print(f"prop_rows: {len(prop_rows)} (expect 22)")

assert mock_client.fixtures_by_date.call_count == 2
assert mock_client.lineups.call_count == 1, "lineups must be fetched ONCE and shared, not once per engine"
assert mock_client.odds.call_count == 1, "odds must be fetched ONCE and shared, not once per engine"
assert len(goal_rows) == 1
assert len(prop_rows) == 22
sample_row = [r for r in prop_rows if r["player"] == home_names[0]][0]
assert sample_row["odds_shots_gt0.5"] == 1.75, "expected mocked player-shots odds to reach the props row"
print("\nALL CHECKS PASSED — shared fetch confirmed, no duplicate API-Football calls.")
