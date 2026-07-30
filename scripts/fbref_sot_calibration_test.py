"""Calibration check for player SHOTS-ON-TARGET, using FBref data (Understat
has no per-player SOT). Reuses the exact same generic helpers already
confirmed for the Understat shots model (players.py): _decayed_rate (position-
grouped shrinkage), build_team_xg (generalized, here for opponent SOT
suppression), prob_over (Negative Binomial dispersion).

Single-league, ~1 season + a slice of the prior season (real history, not
overlap - time-decay handles the age gap). Walk-forward, no lookahead.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from footymodel.backtest import calibration_table
from footymodel.fbref import load_players
from footymodel.players import (DECAY_XI, POSITION_GROUPS, SHOTS_DISPERSION,
                                build_team_xg, _decayed_rate, prob_over)

LINES = [0.5, 1.5]  # SOT lines - lower volume stat than shots, keep to 2 sane ones
TEST_START = "2023-10-01"
MIN_TRAIN_ROWS = 1200
MINUTES_ASSUMED = 85


def fit_and_predict(players: pd.DataFrame, as_of: pd.Timestamp):
    """Mirrors LineupModel's shots-rating fit (position-grouped shrinkage +
    opponent suppression), but standalone for FBref's 'sot' column."""
    past = players[players["date"] < as_of]
    non_sub = past  # FBref summary rows are all "appeared", no starter/sub tag
    pos_by_player = (non_sub.groupby("player_id")["position"]
                     .agg(lambda s: s.mode().iat[0])
                     .map(POSITION_GROUPS).fillna("MID"))
    past = past.assign(pos_group=past["player_id"].map(pos_by_player).fillna("MID"))
    ratings, fallback = _decayed_rate(past, "sot", as_of, DECAY_XI, prior_90s=6.0,
                                      group_col="pos_group")
    team_sot = build_team_xg(past, stat_col="sot")
    opp_fac = (team_sot.groupby("team")["sot_against"].mean()
              / team_sot["sot_against"].mean()).to_dict()
    return ratings, fallback, opp_fac


def evaluate(players: pd.DataFrame) -> pd.DataFrame:
    meta = players.groupby("match_id").agg(date=("date", "first")).reset_index()
    dates = sorted(meta.loc[meta.date >= pd.Timestamp(TEST_START), "date"].unique())
    # team_us equivalent for opponent lookup: use team_id directly (FBref hash)
    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        if len(players[players["date"] < d]) < MIN_TRAIN_ROWS:
            continue
        ratings, fallback, opp_fac = fit_and_predict(players, d)
        day = players[players["date"] == d]
        for url, g in day.groupby("match_id"):
            teams = list(dict.fromkeys(g["team_us"]))
            if len(teams) != 2:
                continue
            opp_of = {teams[0]: teams[1], teams[1]: teams[0]}
            for r in g.itertuples(index=False):
                rate = ratings.get(r.player_id, fallback) * opp_fac.get(opp_of[r.team_us], 1.0)
                rows.append({"rate": rate, "sot": r.sot})
    return pd.DataFrame(rows)


evals = evaluate(load_players())
print(f"Evaluated {len(evals)} player-match SOT predictions\n")
for line in LINES:
    for tag, disp in [("Poisson", None), (f"NB(disp={SHOTS_DISPERSION})", SHOTS_DISPERSION)]:
        p = np.array([prob_over(r, MINUTES_ASSUMED, line, disp) for r in evals["rate"]])
        won = (evals["sot"] > line).values
        brier = np.mean((p - won) ** 2)
        print(f"=== line {line} [{tag}] — n={len(p)} — base rate {won.mean()*100:.1f}% — Brier {brier:.4f} ===")
        print(calibration_table(pd.DataFrame({"p": p, "won": won}))
              .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
        print()
