"""Calibration check for player shots + SOT using WhoScored data (real per-
player minutes and real position codes - see footymodel/whoscored.py, and
compare against scripts/fbref_sot_calibration_test.py's flat-85-minutes
version). Same generic helpers as everywhere else: _decayed_rate
(position-grouped shrinkage), build_team_xg (opponent suppression),
prob_over (Negative Binomial dispersion). Walk-forward, no lookahead.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from footymodel.backtest import calibration_table
from footymodel.whoscored import load_players
from footymodel.players import (DECAY_XI, POSITION_GROUPS, SHOTS_DISPERSION,
                                build_team_xg, _decayed_rate, prob_over)

STAT_LINES = {"shots": [0.5, 1.5, 2.5], "sot": [0.5, 1.5]}
TEST_START = "2023-11-01"
MIN_TRAIN_ROWS = 1200


def fit_and_predict(players: pd.DataFrame, as_of: pd.Timestamp, stat_col: str):
    past = players[players["date"] < as_of]
    non_sub = past[past["position"] != "Sub"]
    pos_by_player = (non_sub.groupby("player_id")["position"]
                     .agg(lambda s: s.mode().iat[0])
                     .map(POSITION_GROUPS).fillna("MID"))
    past = past.assign(pos_group=past["player_id"].map(pos_by_player).fillna("MID"))
    ratings, fallback = _decayed_rate(past, stat_col, as_of, DECAY_XI, prior_90s=6.0,
                                      group_col="pos_group")
    team_stat = build_team_xg(past, stat_col=stat_col)
    against_col = f"{stat_col}_against"
    opp_fac = (team_stat.groupby("team")[against_col].mean()
              / team_stat[against_col].mean()).to_dict()

    # League-wide (not per-team - too noisy at ~19 matches/team/venue) home/away
    # multiplier, same precedent as model.py's single home_adv constant.
    nineties = past["minutes"] / 90.0
    side_agg = past.groupby("side").agg(_s=(stat_col, "sum"), _m=("minutes", "sum"))
    by_side = side_agg["_s"] / (side_agg["_m"] / 90.0)
    overall_p90 = past[stat_col].sum() / nineties.sum()
    venue_fac = (by_side / overall_p90).to_dict()
    return ratings, fallback, opp_fac, venue_fac


def evaluate(players: pd.DataFrame, stat_col: str) -> pd.DataFrame:
    meta = players.groupby("match_id").agg(date=("date", "first")).reset_index()
    dates = sorted(meta.loc[meta.date >= pd.Timestamp(TEST_START), "date"].unique())
    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        if len(players[players["date"] < d]) < MIN_TRAIN_ROWS:
            continue
        ratings, fallback, opp_fac, venue_fac = fit_and_predict(players, d, stat_col)
        day = players[players["date"] == d]
        for match_id, g in day.groupby("match_id"):
            teams = list(dict.fromkeys(g["team_us"]))
            if len(teams) != 2:
                continue
            opp_of = {teams[0]: teams[1], teams[1]: teams[0]}
            for r in g.itertuples(index=False):
                base_rate = ratings.get(r.player_id, fallback) * opp_fac.get(opp_of[r.team_us], 1.0)
                venue_rate = base_rate * venue_fac.get(r.side, 1.0)
                rows.append({"rate": base_rate, "venue_rate": venue_rate,
                            "minutes": r.minutes, "actual": getattr(r, stat_col)})
    return pd.DataFrame(rows)


players = load_players()
print(f"Loaded {len(players)} player-match rows across {players['match_id'].nunique()} matches\n")

for stat_col, lines in STAT_LINES.items():
    evals = evaluate(players, stat_col)
    print(f"##### {stat_col.upper()} — evaluated {len(evals)} player-match predictions #####\n")
    for line in lines:
        for rate_col, rate_tag in [("rate", "no venue"), ("venue_rate", "+venue")]:
            p = np.array([prob_over(r, m, line, None) for r, m in zip(evals[rate_col], evals["minutes"])])
            won = (evals["actual"] > line).values
            brier = np.mean((p - won) ** 2)
            print(f"=== line {line} [Poisson, {rate_tag}] — n={len(p)} — base rate {won.mean()*100:.1f}% — Brier {brier:.4f} ===")
            print(calibration_table(pd.DataFrame({"p": p, "won": won}))
                  .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
            print()
