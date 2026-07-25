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
                          league_mean_xg90: float) -> dict:
    """Per-90 xG rating per player from matches strictly before `as_of`,
    time-decayed and shrunk toward the league mean."""
    past = players[players["date"] < as_of]
    if past.empty:
        return {}
    w = np.exp(-DECAY_XI * (as_of - past["date"]).dt.days.clip(lower=0))
    nineties = past["minutes"] / 90.0
    g = pd.DataFrame({
        "pid": past["player_id"].values,
        "wxg": (w * past["xg"]).values,
        "w90": (w * nineties).values,
    }).groupby("pid").sum()
    # Shrunk per-90 rate: (sum weighted xG + prior) / (sum weighted 90s + prior_n)
    rate = (g["wxg"] + PRIOR_90S * league_mean_xg90) / (g["w90"] + PRIOR_90S)
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


def accuracy_test(test_start: str = "2022-07-01", league: str = "E0") -> pd.DataFrame:
    """Walk-forward: compare lineup-model O/U prob accuracy vs the team-level
    baseline (from evals_main.parquet) on the same matches."""
    from .data import PROCESSED_DIR
    from .understat import load_xg

    players = load_players()
    players = players[players["league"] == league]
    team_xg = build_team_xg(players)

    # Actual totals + team-name join via the xG-merged match table.
    mx = load_xg()
    mx = mx[mx["league"] == league].copy()
    mx["date"] = pd.to_datetime(mx["date"]).dt.normalize()
    mx["total"] = mx["fthg"] + mx["ftag"]

    # Map Understat team titles -> football-data names via date+score is complex;
    # instead work entirely in Understat space: get per-match home/away titles.
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
        lm_xg90 = past_players["xg"].sum() / (past_players["minutes"].sum() / 90.0)
        ratings = player_attack_ratings(players, d, lm_xg90)
        att_fac, def_fac, lg_team_xg = team_factors(team_xg, d)
        fallback = lm_xg90

        for m in meta[meta.date == d].itertuples(index=False):
            hs, as_ = home_line.get(m.match_id, []), away_line.get(m.match_id, [])
            if not hs or not as_:
                continue
            # LINEUP model: attack = sum of starters' player ratings
            h_line = sum(ratings.get(p, fallback) for p in hs) * def_fac.get(m.away_us, 1.0)
            a_line = sum(ratings.get(p, fallback) for p in as_) * def_fac.get(m.home_us, 1.0)
            # TEAM baseline: attack = team-average factor (no lineup info)
            h_team = lg_team_xg * att_fac.get(m.home_us, 1.0) * def_fac.get(m.away_us, 1.0)
            a_team = lg_team_xg * att_fac.get(m.away_us, 1.0) * def_fac.get(m.home_us, 1.0)
            # BLEND: lineup info as a regularized adjustment to the team baseline
            blend_total = 0.5 * (h_line + a_line) + 0.5 * (h_team + a_team)
            rows.append({
                "date": d, "match_id": m.match_id, "over_won": bool(m.total > 2.5),
                "p_over_lineup": _ou_prob_over25(h_line + a_line),
                "p_over_team": _ou_prob_over25(h_team + a_team),
                "p_over_blend": _ou_prob_over25(blend_total),
            })
    return pd.DataFrame(rows)
