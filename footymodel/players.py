"""Phase A — lineup-aware player-level totals model.

Idea: estimate each team's attacking output for a match from the actual starting
XI's player ratings, not a static team average. When a high-xG player is missing,
the team's expected goals drop — the information the market prices via lineups.

    player attack rating = time-decayed, shrunk xG-per-90 (from past matches)
    team lineup xG       = sum of starting XI player ratings  (x opponent defence)
    total goals          = home_xG + away_xG -> Poisson -> Over/Under prob

We compare this model's O/U prediction accuracy (Brier / log-loss) against the
team-level baseline. NOTE: accuracy is necessary but not sufficient — profit
needs live lineups + fast execution (Phase B), which cannot be backtested on
opening/closing snapshots alone.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import poisson

from .understat import PLAYER_OUTPUT

# Shrinkage: a player's rating is pulled toward the league mean by PRIOR_90S
# worth of average performance — protects thin samples (new/fringe players).
PRIOR_90S = 5.0
DECAY_XI = 0.0018  # per-day time decay, matching the team model


def load_players() -> pd.DataFrame:
    df = pd.read_parquet(PLAYER_OUTPUT)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["started"] = df["position"] != "Sub"
    return df


def player_attack_ratings(players: pd.DataFrame, as_of: pd.Timestamp,
                          league_mean_c90: float, xa_weight: float = 0.5,
                          prior_90s: float = PRIOR_90S) -> dict:
    """Per-90 attacking-CONTRIBUTION rating per player (xG + xa_weight*xA) from
    matches strictly before `as_of`, time-decayed and shrunk toward league mean.
    Including xA credits playmakers whose absence lowers team output."""
    past = players[players["date"] < as_of]
    if past.empty:
        return {}
    w = np.exp(-DECAY_XI * (as_of - past["date"]).dt.days.clip(lower=0))
    contrib = past["xg"] + xa_weight * past["xa"]
    nineties = past["minutes"] / 90.0
    g = pd.DataFrame({
        "pid": past["player_id"].values,
        "wc": (w * contrib).values,
        "w90": (w * nineties).values,
    }).groupby("pid").sum()
    rate = (g["wc"] + prior_90s * league_mean_c90) / (g["w90"] + prior_90s)
    return rate.to_dict()


def player_defence_ratings(players_with_xga: pd.DataFrame, as_of: pd.Timestamp,
                          league_mean_dc90: float, prior_90s: float = PRIOR_90S) -> dict:
    """Per-90 defensive-concession rating per player: the team's xG-against in
    matches they played, minutes-weighted, time-decayed, shrunk to league mean.

    This is a proxy (Understat has no individual defensive-action xG) standard
    in public analytics: "goals/xG conceded per 90 while on the pitch." Lower =
    better defender. Requires `xg_against` joined onto each player-match row."""
    past = players_with_xga[players_with_xga["date"] < as_of]
    if past.empty:
        return {}
    w = np.exp(-DECAY_XI * (as_of - past["date"]).dt.days.clip(lower=0))
    nineties = past["minutes"] / 90.0
    g = pd.DataFrame({
        "pid": past["player_id"].values,
        "wxga": (w * past["xg_against"] * nineties).values,
        "w90": (w * nineties).values,
    }).groupby("pid").sum()
    rate = (g["wxga"] + prior_90s * league_mean_dc90) / (g["w90"] + prior_90s)
    return rate.to_dict()


def team_factors(team_xg: pd.DataFrame, as_of: pd.Timestamp) -> tuple[dict, dict, float]:
    """Per-team attack and defence multipliers (vs league avg) from past matches.
    Returns (attack_factor, defence_factor, league_avg_team_xg)."""
    past = team_xg[team_xg["date"] < as_of]
    if past.empty:
        return {}, {}, 1.35
    lg = past["xg_for"].mean()
    att = (past.groupby("team")["xg_for"].mean() / lg).to_dict()
    dfn = (past.groupby("team")["xg_against"].mean() / past["xg_against"].mean()).to_dict()
    return att, dfn, lg


def build_team_xg(players: pd.DataFrame) -> pd.DataFrame:
    """Aggregate player-match rows to team-match xG for/against (for defence)."""
    tm = players.groupby(["match_id", "date", "league", "team_us", "side"], as_index=False).agg(
        xg_for=("xg", "sum"))
    # opponent xg = the other side's xg_for in the same match
    opp = tm.copy()
    opp["side"] = opp["side"].map({"h": "a", "a": "h"})
    opp = opp.rename(columns={"xg_for": "xg_against", "team_us": "opp"})[
        ["match_id", "side", "xg_against"]]
    tm = tm.merge(opp, on=["match_id", "side"])
    return tm.rename(columns={"team_us": "team"})


def _ou_prob_over25(total_mean: float) -> float:
    """P(total goals > 2.5) for a Poisson total."""
    return float(1.0 - poisson.cdf(2, total_mean))


def accuracy_test(test_start: str = "2022-07-01", league: str = "E0",
                  xa_weight: float = 0.5, prior_90s: float = PRIOR_90S) -> pd.DataFrame:
    """Walk-forward. Returns per-match RAW expected totals for team-average,
    half-lineup (attack only), and full-lineup (attack+defence) models, plus
    outcome. Calibration/blending/metrics done downstream."""
    players = load_players()
    players = players[players["league"] == league]
    team_xg = build_team_xg(players)
    # join each player-match row to its team's xG-against that match (for defence ratings)
    players = players.merge(
        team_xg[["match_id", "team", "xg_against"]],
        left_on=["match_id", "team_us"], right_on=["match_id", "team"], how="left")

    # Home advantage: mean home xG / mean away xG in the data.
    hm = team_xg[team_xg["side"] == "h"]["xg_for"].mean()
    am = team_xg[team_xg["side"] == "a"]["xg_for"].mean()
    home_mult = float(np.sqrt(hm / am)) if am else 1.0

    # Work in Understat space: per-match home/away titles.
    meta = players.groupby("match_id").agg(
        date=("date", "first"), league=("league", "first"),
        home_us=("home_us", "first"), away_us=("away_us", "first")).reset_index()
    # actual total from player goals (== match goals up to rare own goals)
    tot = players.groupby("match_id")["goals"].sum().rename("total").reset_index()
    meta = meta.merge(tot, on="match_id")

    starters = players[players["started"]]
    home_line = starters[starters.side == "h"].groupby("match_id")["player_id"].apply(list)
    away_line = starters[starters.side == "a"].groupby("match_id")["player_id"].apply(list)

    test_start = pd.Timestamp(test_start)
    dates = sorted(meta.loc[meta.date >= test_start, "date"].unique())
    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        past_players = players[players.date < d]
        if len(past_players) < 5000:
            continue
        # league mean contribution per 90 (for shrinkage prior)
        contrib = past_players["xg"] + xa_weight * past_players["xa"]
        lm_c90 = contrib.sum() / (past_players["minutes"].sum() / 90.0)
        ratings = player_attack_ratings(players, d, lm_c90, xa_weight, prior_90s)
        att_fac, def_fac, lg_team_xg = team_factors(team_xg, d)
        fallback = lm_c90

        lm_dc90 = past_players["xg_against"].fillna(lg_team_xg).mean()  # ~league avg xGA/match
        dratings = player_defence_ratings(past_players, d, lm_dc90, prior_90s)
        dfallback = lm_dc90

        for m in meta[meta.date == d].itertuples(index=False):
            hs, as_ = home_line.get(m.match_id, []), away_line.get(m.match_id, [])
            if not hs or not as_:
                continue
            # ATTACK: starter-contribution sum as an ABSOLUTE attack multiplier.
            # Reference full-strength sum ~ 1.5*lg_team_xg (xG + xa_weight*xA);
            # residual bias in that constant is removed by downstream scale calib.
            ref = 1.5 * lg_team_xg
            att_line_h = sum(ratings.get(p, fallback) for p in hs) / ref
            att_line_a = sum(ratings.get(p, fallback) for p in as_) / ref

            # DEFENCE: starting back-line's average xGA-while-playing, vs league avg.
            dline_h = np.mean([dratings.get(p, dfallback) for p in hs]) / lg_team_xg
            dline_a = np.mean([dratings.get(p, dfallback) for p in as_]) / lg_team_xg

            # HALF-LINEUP (attack from XI, defence = team average) — the original test.
            h_half = lg_team_xg * att_line_h * def_fac.get(m.away_us, 1.0) * home_mult
            a_half = lg_team_xg * att_line_a * def_fac.get(m.home_us, 1.0) / home_mult
            # FULL-LINEUP (attack AND defence both from the starting XI).
            h_full = lg_team_xg * att_line_h * dline_a * home_mult
            a_full = lg_team_xg * att_line_a * dline_h / home_mult
            # TEAM baseline (no lineup info at all).
            h_team = lg_team_xg * att_fac.get(m.home_us, 1.0) * def_fac.get(m.away_us, 1.0) * home_mult
            a_team = lg_team_xg * att_fac.get(m.away_us, 1.0) * def_fac.get(m.home_us, 1.0) / home_mult
            rows.append({
                "date": d, "match_id": m.match_id, "over_won": bool(m.total > 2.5),
                "exp_team": h_team + a_team, "exp_line": h_half + a_half,
                "exp_full": h_full + a_full,
            })
    return pd.DataFrame(rows)
