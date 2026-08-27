"""Dry-run the full Phase B pipeline with a MOCKED API-Football response
(no network, no API key spent) to validate process_fixture() end-to-end:
team-id matching, lineup parsing, player-name matching, odds parsing, EV calc.

Uses two real teams/rosters from our historical data as stand-ins.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import MagicMock

import pandas as pd

from footymodel.live import namematch
from footymodel.live.engine import LiveWatcher
from footymodel.players import load_players

players = load_players()
home_us, away_us = "Manchester City", "Arsenal"
home_roster = namematch.team_roster_index(players, "E0", home_us)
away_roster = namematch.team_roster_index(players, "E0", away_us)
home_names = list(home_roster.keys())[:11]
away_names = list(away_roster.keys())[:11]

fixture = {
    "fixture": {"id": 999001, "date": (pd.Timestamp.now() + pd.Timedelta(minutes=30)).isoformat()},
    "teams": {"home": {"id": 50, "name": home_us}, "away": {"id": 42, "name": away_us}},
}
mock_lineups = [
    {"team": {"id": 50, "name": home_us},
     "startXI": [{"player": {"name": n}} for n in home_names]},
    {"team": {"id": 42, "name": away_us},
     "startXI": [{"player": {"name": n}} for n in away_names]},
]
mock_odds = [{"bookmakers": [
    {"bets": [{"name": "Goals Over/Under",
              "values": [{"value": "Over 2.5", "odd": "1.85"},
                        {"value": "Under 2.5", "odd": "1.95"}]}]},
    {"bets": [{"name": "Goals Over/Under",  # a second bookmaker -> tests "best price" logic
              "values": [{"value": "Over 2.5", "odd": "1.92"},
                        {"value": "Under 2.5", "odd": "1.88"}]}]},
]}]

mock_client = MagicMock()
mock_client.lineups.return_value = mock_lineups
mock_client.odds.return_value = mock_odds

watcher = LiveWatcher(client=mock_client)
row = watcher.process_fixture("E0", fixture, mock_lineups)

print("\n=== process_fixture() result ===")
if row is None:
    print("FAILED: returned None (check unmatched-player / team-match warnings above)")
    sys.exit(1)
for k, v in row.items():
    print(f"  {k}: {v}")

assert row["n_home_starters_matched"] == 11, "expected all 11 home starters matched"
assert row["n_away_starters_matched"] == 11, "expected all 11 away starters matched"
assert row["odds_over25"] == 1.92, "expected BEST price across bookmakers (1.92), not first (1.85)"
assert row["odds_under25"] == 1.95, "expected BEST price across bookmakers (1.95), not first (1.88)"
print("\nALL CHECKS PASSED — pipeline plumbing is correct end-to-end.")
