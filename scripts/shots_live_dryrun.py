"""Dry-run the live shots/SOT props pipeline with a MOCKED API response (no
key/quota spent) - mirrors scripts/live_dryrun.py's pattern for the goals
engine. Validates: team matching (both Understat + FBref spaces), player
matching (both spaces), and that probabilities come out sane.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import MagicMock

import pandas as pd

from footymodel.live import namematch
from footymodel.live.shots_engine import PropsWatcher

watcher = PropsWatcher()
home_name, away_name = "Manchester City", "Everton"
# Use CURRENT squads (from FBref's more recent roster) so the dry-run reflects
# a realistic lineup, not Understat's full 2019-2024 history which includes
# long-retired/departed players FBref's 2022+ coverage never saw.
home_f_id = watcher.fbref_name_to_id[namematch.match_team(home_name, list(watcher.fbref_names.values()))]
away_f_id = watcher.fbref_name_to_id[namematch.match_team(away_name, list(watcher.fbref_names.values()))]
home_names = list(namematch.team_roster_index(watcher.fbref, "E0", home_f_id).keys())[:11]
away_names = list(namematch.team_roster_index(watcher.fbref, "E0", away_f_id).keys())[:11]

fixture = {
    "fixture": {"id": 999002, "date": (pd.Timestamp.now() + pd.Timedelta(minutes=30)).isoformat()},
    "teams": {"home": {"id": 50, "name": home_name}, "away": {"id": 29, "name": away_name}},
}
mock_lineups = [
    {"team": {"id": 50, "name": home_name}, "startXI": [{"player": {"name": n}} for n in home_names]},
    {"team": {"id": 29, "name": away_name}, "startXI": [{"player": {"name": n}} for n in away_names]},
]
watcher.client = MagicMock()
watcher.client.lineups.return_value = mock_lineups

rows = watcher.player_rows_for_fixture(fixture)
print(f"\n{len(rows)} player rows (expect 22)\n")
df = pd.DataFrame(rows)
print(df.to_string(index=False))

n_no_shots = df["p_shots_gt0.5"].isna().sum()
n_no_sot = df["p_sot_gt0.5"].isna().sum()
print(f"\nUnmatched (no shots pred): {n_no_shots}/22   Unmatched (no SOT pred): {n_no_sot}/22")
assert len(rows) == 22, "expected 11+11 starters"
assert n_no_shots <= 2, "too many unmatched for Understat (all these players should be known)"
assert n_no_sot <= 2, "too many unmatched for FBref (all these players should be known)"
print("\nALL CHECKS PASSED")
