"""Phase A — lineup-aware player-level totals model. CONFIRMED (see RESULTS.md):
pooled t=3.04 across big-5 leagues (5,329 matches) for the full-lineup
(attack+defence from the actual starting XI) model vs a team-average baseline.

    player attack rating  = time-decayed, shrunk (xG + xa_weight*xA) per-90
    player defence rating = time-decayed, shrunk team-xG-conceded-while-playing
                             per-90 (proxy; Understat has no individual
                             defensive-action xG)
    team lineup attack    = sum of starting XI's attack ratings
    team lineup defence   = mean of starting XI's defence ratings
    total goals           = home_xG + away_xG -> Poisson -> Over/Under prob

`LineupModel` is the single source of truth for this prediction — both the
backtest (`accuracy_test`) and the live engine (`live/engine.py`) call it, so
what we validated is exactly what runs live. NOTE: this predicts accuracy, not
profit by itself — the closing line already prices lineups; real edge (if any)
lives in the live window right after lineups drop (Phase B).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import poisson

from .understat import PLAYER_OUTPUT

# Shrinkage: a player's rating is pulled toward the league mean by PRIOR_90S
# worth of average performance — protects thin samples (new/fringe players).
PRIOR_90S = 6.0
XA_WEIGHT = 0.5
DECAY_XI = 0.0018  # per-day time decay, matching the team model

# Confirmed best blend from the big-5 test (RESULTS.md): 25% team-average +
# 75% full-lineup. blend_w is the TEAM weight.
BEST_BLEND_W = 0.25


def load_players() -> pd.DataFrame:
    df = pd.read_parquet(PLAYER_OUTPUT)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["started"] = df["position"] != "Sub"
    return df


def build_team_xg(players: pd.DataFrame) -> pd.DataFrame:
    """Aggregate player-match rows to team-match xG for/against (for defence)."""
    tm = players.groupby(["match_id", "date", "league", "team_us", "side"], as_index=False).agg(
        xg_for=("xg", "sum"))
    opp = tm.copy()
    opp["side"] = opp["side"].map({"h": "a", "a": "h"})
    opp = opp.rename(columns={"xg_for": "xg_against", "team_us": "opp"})[
        ["match_id", "side", "xg_against"]]
    tm = tm.merge(opp, on=["match_id", "side"])
    return tm.rename(columns={"team_us": "team"})


def _ou_prob_over25(total_mean: float) -> float:
    return float(1.0 - poisson.cdf(2, total_mean))


@dataclass
class LineupModel:
    """Fit once (as of a given date) on a league's player history; predict
    totals for any home/away starting XI. Shared by backtest and live engine."""

    league: str
    as_of: pd.Timestamp
    xa_weight: float = XA_WEIGHT
    prior_90s: float = PRIOR_90S
    blend_w: float = BEST_BLEND_W

    attack_ratings: dict = field(default_factory=dict, repr=False)
    defence_ratings: dict = field(default_factory=dict, repr=False)
    att_fac: dict = field(default_factory=dict, repr=False)
    def_fac: dict = field(default_factory=dict, repr=False)
    lg_team_xg: float = 1.35
    home_mult: float = 1.0
    attack_fallback: float = 0.0
    defence_fallback: float = 0.0
    n_past_matches: int = 0

    @classmethod
    def fit(cls, players: pd.DataFrame, league: str, as_of: pd.Timestamp,
           xa_weight: float = XA_WEIGHT, prior_90s: float = PRIOR_90S,
           blend_w: float = BEST_BLEND_W) -> "LineupModel":
        players = players[players["league"] == league]
        team_xg = build_team_xg(players)
        players = players.merge(
            team_xg[["match_id", "team", "xg_against"]],
            left_on=["match_id", "team_us"], right_on=["match_id", "team"], how="left")

        as_of = pd.Timestamp(as_of)
        past = players[players["date"] < as_of]
        past_team_xg = team_xg[team_xg["date"] < as_of]

        m = cls(league=league, as_of=as_of, xa_weight=xa_weight,
                prior_90s=prior_90s, blend_w=blend_w)
        m.n_past_matches = past["match_id"].nunique()
        if past.empty or past_team_xg.empty:
            return m  # caller should check n_past_matches before trusting predictions

        # Attack ratings.
        w = np.exp(-DECAY_XI * (as_of - past["date"]).dt.days.clip(lower=0))
        contrib = past["xg"] + xa_weight * past["xa"]
        nineties = past["minutes"] / 90.0
        lm_c90 = contrib.sum() / nineties.sum()
        g = pd.DataFrame({"pid": past["player_id"].values,
                         "wc": (w * contrib).values, "w90": (w * nineties).values}
                        ).groupby("pid").sum()
        m.attack_ratings = ((g["wc"] + prior_90s * lm_c90) / (g["w90"] + prior_90s)).to_dict()
        m.attack_fallback = lm_c90

        # Team factors (attack/defence multipliers, league avg xG).
        m.lg_team_xg = past_team_xg["xg_for"].mean()
        m.att_fac = (past_team_xg.groupby("team")["xg_for"].mean() / m.lg_team_xg).to_dict()
        m.def_fac = (past_team_xg.groupby("team")["xg_against"].mean()
                    / past_team_xg["xg_against"].mean()).to_dict()

        # Defence ratings (proxy: team xGA in matches played, minutes-weighted).
        lm_dc90 = past["xg_against"].fillna(m.lg_team_xg).mean()
        gd = pd.DataFrame({"pid": past["player_id"].values,
                          "wxga": (w * past["xg_against"] * nineties).values,
                          "w90": (w * nineties).values}).groupby("pid").sum()
        m.defence_ratings = ((gd["wxga"] + prior_90s * lm_dc90) / (gd["w90"] + prior_90s)).to_dict()
        m.defence_fallback = lm_dc90

        # Home advantage.
        hm = past_team_xg[past_team_xg["side"] == "h"]["xg_for"].mean()
        am = past_team_xg[past_team_xg["side"] == "a"]["xg_for"].mean()
        m.home_mult = float(np.sqrt(hm / am)) if am else 1.0
        return m

    def predict(self, home_starters: list, away_starters: list,
               home_team: str, away_team: str) -> dict:
        """Predict total-goals distribution for a fixture given the ACTUAL
        starting XIs (player ids matching the training data's `player_id`)."""
        ref = 1.5 * self.lg_team_xg
        att_h = sum(self.attack_ratings.get(p, self.attack_fallback) for p in home_starters) / ref
        att_a = sum(self.attack_ratings.get(p, self.attack_fallback) for p in away_starters) / ref
        dln_h = np.mean([self.defence_ratings.get(p, self.defence_fallback)
                        for p in home_starters]) / self.lg_team_xg
        dln_a = np.mean([self.defence_ratings.get(p, self.defence_fallback)
                        for p in away_starters]) / self.lg_team_xg

        h_full = self.lg_team_xg * att_h * dln_a * self.home_mult
        a_full = self.lg_team_xg * att_a * dln_h / self.home_mult
        h_team = (self.lg_team_xg * self.att_fac.get(home_team, 1.0)
                 * self.def_fac.get(away_team, 1.0) * self.home_mult)
        a_team = (self.lg_team_xg * self.att_fac.get(away_team, 1.0)
                 * self.def_fac.get(home_team, 1.0) / self.home_mult)

        exp_full, exp_team = h_full + a_full, h_team + a_team
        exp_blend = self.blend_w * exp_team + (1 - self.blend_w) * exp_full
        return {
            "exp_team": exp_team, "exp_full": exp_full, "exp_blend": exp_blend,
            "p_over25_team": _ou_prob_over25(exp_team),
            "p_over25_full": _ou_prob_over25(exp_full),
            "p_over25_blend": _ou_prob_over25(exp_blend),
        }


def accuracy_test(test_start: str = "2022-07-01", league: str = "E0",
                  xa_weight: float = XA_WEIGHT, prior_90s: float = PRIOR_90S,
                  min_train_rows: int = 5000) -> pd.DataFrame:
    """Walk-forward backtest using LineupModel (identical to what live uses).
    Returns raw expected totals for team/full-lineup models + outcome, for
    downstream calibration/blend sweeps (see scripts/lineup_test.py)."""
    players = load_players()
    league_players = players[players["league"] == league]

    meta = league_players.groupby("match_id").agg(
        date=("date", "first"), home_us=("home_us", "first"),
        away_us=("away_us", "first")).reset_index()
    tot = league_players.groupby("match_id")["goals"].sum().rename("total").reset_index()
    meta = meta.merge(tot, on="match_id")

    starters = league_players[league_players["started"]]
    home_line = starters[starters.side == "h"].groupby("match_id")["player_id"].apply(list)
    away_line = starters[starters.side == "a"].groupby("match_id")["player_id"].apply(list)

    test_start = pd.Timestamp(test_start)
    dates = sorted(meta.loc[meta.date >= test_start, "date"].unique())
    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        past_rows = len(league_players[league_players["date"] < d])
        if past_rows < min_train_rows:
            continue
        model = LineupModel.fit(players, league, d, xa_weight, prior_90s)
        for m in meta[meta.date == d].itertuples(index=False):
            hs, as_ = home_line.get(m.match_id, []), away_line.get(m.match_id, [])
            if not hs or not as_:
                continue
            pred = model.predict(hs, as_, m.home_us, m.away_us)
            rows.append({"date": d, "match_id": m.match_id, "over_won": bool(m.total > 2.5),
                        "exp_team": pred["exp_team"], "exp_full": pred["exp_full"]})
    return pd.DataFrame(rows)
