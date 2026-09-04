"""Dry-run run_all.py's shared-fetch orchestration with a MOCKED API response
(no network, no quota spent). Validates the actual reason run_all.py exists:
ONE fixtures-by-date call and ONE lineups-per-fixture call feed BOTH the
goals and player-props engines, not two independent fetches each.

Uses tmp paths for the seen-fixtures/CSV state so this doesn't touch the
real project's live-polling files.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live import calendar as fxcal
from footymodel.live import engine, match_detail, run_all, shots_engine, watchlist
from footymodel.live import namematch
from footymodel.players import load_players

tmp = Path(tempfile.mkdtemp())
engine.SEEN_FIXTURES_FILE = tmp / "seen.json"
engine.LIVE_LOG = tmp / "goals.csv"
run_all.LIVE_LOG = engine.LIVE_LOG
shots_engine.PROPS_LOG = tmp / "props.csv"
run_all.PROPS_LOG = shots_engine.PROPS_LOG
match_detail.MATCH_DETAIL_LOG = tmp / "match_detail.jsonl"
run_all.UPCOMING_LOG = tmp / "upcoming_fixtures.json"
fxcal.CALENDAR_FILE = tmp / "fixture_calendar.json"
fxcal.UPCOMING_LOG = run_all.UPCOMING_LOG
fxcal.UNDERSTAT_DIR = tmp
watchlist.write_watchlist = lambda upcoming: []

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
# A fixture whose kickoff already passed (an hour ago) but still has
# confirmed lineups available - this is the exact shape of the 5 real
# matches a GitHub Actions cron gap lost over the 2026-08-30/31 weekend.
# Its lineup/odds data is identical to `fixture`'s (this test only cares
# about the window logic, not a second distinct roster).
fixture_past = {
    "fixture": {"id": 999004,
               "date": (pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=1)).isoformat()},
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
mock_client.fixtures_by_date.side_effect = lambda date_str: [fixture, fixture_past]
mock_client.lineups.return_value = mock_lineups
mock_client.odds.return_value = mock_odds

run_all.ApiFootballClient = lambda: mock_client

goal_rows, prop_rows = run_all.run_once()

print(f"fixtures_by_date calls: {mock_client.fixtures_by_date.call_count} (expect 3 — today+tomorrow+day-after)")
print(f"lineups calls: {mock_client.lineups.call_count} (expect 2 — one per unique fixture, SHARED across both engines)")
print(f"odds calls: {mock_client.odds.call_count} (expect 2 — one per unique fixture, SHARED across both engines)")
print(f"goal_rows: {len(goal_rows)} (expect 2 — both the future AND the already-kicked-off fixture)")
print(f"prop_rows: {len(prop_rows)} (expect 44 — 22 per fixture)")

assert mock_client.fixtures_by_date.call_count == 3
assert mock_client.lineups.call_count == 2, "lineups must be fetched ONCE PER FIXTURE and shared, not once per engine"
assert mock_client.odds.call_count == 2, "odds must be fetched ONCE PER FIXTURE and shared, not once per engine"
assert len(goal_rows) == 2
assert any(r["fixture_id"] == fixture_past["fixture"]["id"] for r in goal_rows), (
    "expected the already-kicked-off fixture to still be logged thanks to the widened backward window"
)
assert len(prop_rows) == 44
sample_row = [r for r in prop_rows if r["player"] == home_names[0]][0]
assert sample_row["odds_shots_gt0.5"] == 1.75, "expected mocked player-shots odds to reach the props row"

upcoming = json.loads(run_all.UPCOMING_LOG.read_text())
assert len(upcoming) == 1 and upcoming[0]["fixture_id"] == fixture["fixture"]["id"], (
    "expected only the still-upcoming fixture in upcoming_fixtures.json - the already-kicked-off "
    "one must NOT appear there even though it does get a real prediction"
)
print(f"upcoming_fixtures.json: {len(upcoming)} row(s), fixture_id={upcoming[0]['fixture_id']}")

print("\nALL CHECKS PASSED — shared fetch confirmed, no duplicate API-Football calls, "
      "past-kickoff fixture recovered.")
