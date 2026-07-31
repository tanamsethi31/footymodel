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
# Mocked odds mirror the REAL shape confirmed against a live API-Football key
# (2026-07-31, a Boca Juniors CONMEBOL fixture): "{name} - N+" values under
# "Home/Away Player Shots" and "Player Shots On Target". Uses the first home
# starter by name so the odds-matching path is exercised end to end.
sample_player = home_names[0]
mock_odds = [{"bookmakers": [{"bets": [
    {"name": "Home Player Shots", "values": [
        {"value": f"{sample_player} - 1+", "odd": "1.80"},
        {"value": f"{sample_player} - 2+", "odd": "3.50"},
    ]},
    {"name": "Player Shots On Target", "values": [
        {"value": f"{sample_player} - 1+", "odd": "2.50"},
    ]},
]}]}]

watcher.client = MagicMock()
watcher.client.lineups.return_value = mock_lineups
watcher.client.odds.return_value = mock_odds

rows = watcher.player_rows_for_fixture(fixture, mock_lineups)
print(f"\n{len(rows)} player rows (expect 22)\n")
df = pd.DataFrame(rows)
print(df.to_string(index=False))

n_no_shots = df["p_shots_gt0.5"].isna().sum()
n_no_sot = df["p_sot_gt0.5"].isna().sum()
print(f"\nUnmatched (no shots pred): {n_no_shots}/22   Unmatched (no SOT pred): {n_no_sot}/22")
assert len(rows) == 22, "expected 11+11 starters"
assert n_no_shots <= 2, "too many unmatched for Understat (all these players should be known)"
assert n_no_sot <= 2, "too many unmatched for FBref (all these players should be known)"

sample_row = df[df["player"] == sample_player].iloc[0]
assert sample_row["odds_shots_gt0.5"] == 1.80, "expected mocked odds matched to the sample player"
assert sample_row["odds_shots_gt1.5"] == 3.50
assert sample_row["odds_sot_gt0.5"] == 2.50
if sample_row["p_shots_gt0.5"] is not None:
    assert sample_row["ev_shots_gt0.5"] == round(sample_row["p_shots_gt0.5"] * 1.80 - 1.0, 3)
print("\nALL CHECKS PASSED")
