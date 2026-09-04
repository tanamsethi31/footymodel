"""Data-free checks for the pre-lineup player-props watchlist."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live import watchlist as wl

tmp = Path(tempfile.mkdtemp())

as_of = pd.Timestamp("2026-09-04")
rows = []
for mid, day, started, pid, name, pos in [
    ("m1", "2026-08-20", True, "p_old", "Old Striker", "FW"),
    ("m2", "2026-08-28", True, "p_gk", "Keeper", "GK"),
    ("m2", "2026-08-28", True, "p_fw", "Hot Forward", "FW"),
    ("m2", "2026-08-28", True, "p_mf", "Quiet Mid", "MC"),
    ("m2", "2026-08-28", False, "p_sub", "Bench", "FW"),
    ("m3", "2026-09-01", True, "p_gk", "Keeper", "GK"),
    ("m3", "2026-09-01", True, "p_fw", "Hot Forward", "FW"),
    ("m3", "2026-09-01", True, "p_mf", "Quiet Mid", "MC"),
]:
    rows.append({
        "league": "E0", "team_us": "Home FC", "match_id": mid,
        "date": pd.Timestamp(day), "started": started,
        "player_id": pid, "player": name, "position": pos,
        "minutes": 90, "xg": 0.1, "xa": 0.0, "shots": 2, "goals": 0,
        "home_us": "Home FC", "away_us": "Away FC", "side": "h",
    })
rows.append({
    "league": "E0", "team_us": "Away FC", "match_id": "m3",
    "date": pd.Timestamp("2026-09-01"), "started": True,
    "player_id": "p_aw", "player": "Away Ace", "position": "FW",
    "minutes": 90, "xg": 0.2, "xa": 0.0, "shots": 3, "goals": 0,
    "home_us": "Home FC", "away_us": "Away FC", "side": "a",
})
players = pd.DataFrame(rows)

cands = wl.recent_non_gk_starters(players, "E0", "Home FC", as_of, n_matches=6)
names = {n for _, n in cands}
assert names == {"Hot Forward", "Quiet Mid", "Old Striker"}, names
assert "Keeper" not in names
assert "Bench" not in names


def fake_predict(pid, opp, minutes, line, side):
    return {"p_fw": 0.81, "p_mf": 0.40, "p_old": 0.55, "p_aw": 0.70}[pid]


class Dummy:
    def predict_player_shots(self, pid, opp, minutes, line, side="h"):
        return fake_predict(pid, opp, minutes, line, side)


ranked = wl.watch_side(Dummy(), cands, "Away FC", "h", per_side=2, predict_fn=fake_predict)
assert [r["player"] for r in ranked] == ["Hot Forward", "Old Striker"], ranked
assert ranked[0]["p_shots_gt0.5"] == 0.81

fx = {
    "fixture_id": "us_1",
    "home": "Home FC",
    "away": "Away FC",
    "kickoff": "2026-09-05T14:00:00+00:00",
}
rec = wl.watchlist_for_fixture(fx, players, Dummy(), predict_fn=fake_predict)
assert rec["home_watch"][0]["player"] == "Hot Forward"
assert rec["away_watch"][0]["player"] == "Away Ace"

built = wl.build_watchlist([fx], players=players, model=Dummy())
assert len(built) == 1
assert built[0]["fixture_id"] == "us_1"

miss = wl.watchlist_for_fixture(
    {"fixture_id": 1, "home": "Not A Team", "away": "Also Fake",
     "kickoff": "2026-09-05T14:00:00+00:00"},
    players, Dummy(), predict_fn=fake_predict,
)
assert miss is None

# Prior-season starters must not leak into a new campaign's watchlist.
old_season_rows = []
for mid, day, pid, name in [
    ("o1", "2026-05-20", "p_salah", "Mohamed Salah"),
    ("o2", "2026-05-24", "p_salah", "Mohamed Salah"),
]:
    old_season_rows.append({
        "league": "E0", "team_us": "Liverpool", "match_id": mid,
        "date": pd.Timestamp(day), "started": True,
        "player_id": pid, "player": name, "position": "FW",
        "minutes": 90, "xg": 0.3, "xa": 0.0, "shots": 3, "goals": 0,
        "home_us": "Liverpool", "away_us": "Rival FC", "side": "h",
    })
new_season_rows = [{
    "league": "E0", "team_us": "Liverpool", "match_id": "n1",
    "date": pd.Timestamp("2026-08-23"), "started": True,
    "player_id": "p_gakpo", "player": "Cody Gakpo", "position": "FW",
    "minutes": 90, "xg": 0.2, "xa": 0.0, "shots": 2, "goals": 0,
    "home_us": "Liverpool", "away_us": "Opponent", "side": "h",
}]
liverpool_players = pd.DataFrame(old_season_rows + new_season_rows)
as_of_new = pd.Timestamp("2026-09-04")
liv_cands = wl.recent_non_gk_starters(liverpool_players, "E0", "Liverpool", as_of_new)
liv_names = {n for _, n in liv_cands}
assert "Mohamed Salah" not in liv_names, liv_names
assert "Cody Gakpo" in liv_names, liv_names

print("watchlist_test: OK")
