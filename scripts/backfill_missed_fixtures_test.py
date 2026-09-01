"""Test scripts/backfill_missed_fixtures.py's backfill() against a MOCKED
API response (no network, no quota spent) - confirms it recovers a fixture
whose kickoff has already passed, using the same process_one_fixture helper
(and the same seen-set/CSV files) run_all.py's regular poll shares, and that
re-running it for an already-recovered date is a safe no-op."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for footymodel.*
sys.path.insert(0, str(Path(__file__).resolve().parent))          # scripts/, for backfill_missed_fixtures

import pandas as pd

import backfill_missed_fixtures
from footymodel.live import engine, match_detail, namematch
import footymodel.live.shots_engine as shots_engine
from footymodel.players import load_players

tmp = Path(tempfile.mkdtemp())
engine.SEEN_FIXTURES_FILE = tmp / "seen.json"
engine.LIVE_LOG = tmp / "goals.csv"
backfill_missed_fixtures.LIVE_LOG = engine.LIVE_LOG
shots_engine.PROPS_LOG = tmp / "props.csv"
backfill_missed_fixtures.PROPS_LOG = shots_engine.PROPS_LOG
match_detail.MATCH_DETAIL_LOG = tmp / "match_detail.jsonl"

players = load_players()
home_us, away_us = "Manchester City", "Everton"
home_names = list(namematch.team_roster_index(players, "E0", home_us).keys())[:11]
away_names = list(namematch.team_roster_index(players, "E0", away_us).keys())[:11]

past_fixture = {
    "fixture": {"id": 999005,
               "date": (pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=20)).isoformat()},
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
]}]}]

mock_client = MagicMock()
mock_client.fixtures_by_date.return_value = [past_fixture]
mock_client.lineups.return_value = mock_lineups
mock_client.odds.return_value = mock_odds

backfill_missed_fixtures.ApiFootballClient = lambda: mock_client

goal_rows, prop_rows = backfill_missed_fixtures.backfill(["2026-08-30"])

print(f"fixtures_by_date calls: {mock_client.fixtures_by_date.call_count} (expect 1 - exactly the given date)")
print(f"goal_rows: {len(goal_rows)} (expect 1)")

assert mock_client.fixtures_by_date.call_count == 1, "backfill should fetch exactly the given date(s), nothing more"
assert len(goal_rows) == 1
assert goal_rows[0]["fixture_id"] == 999005, "expected the 20-hours-in-the-past fixture to be recovered"

# Running it again for the same date must be a no-op - the fixture is now `seen`.
goal_rows2, prop_rows2 = backfill_missed_fixtures.backfill(["2026-08-30"])
assert goal_rows2 == [], "re-running backfill for an already-recovered fixture must not double-log it"

print("ALL CHECKS PASSED — backfill recovers a past-kickoff fixture and is idempotent on re-run.")
