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
from scipy.stats import nbinom, poisson

from .understat import PLAYER_OUTPUT

# Shrinkage: a player's rating is pulled toward the league mean by PRIOR_90S
# worth of average performance — protects thin samples (new/fringe players).
PRIOR_90S = 6.0
XA_WEIGHT = 0.5
DECAY_XI = 0.0018  # per-day time decay, matching the team model

# Confirmed best blend from the big-5 test (RESULTS.md): 25% team-average +
# 75% full-lineup. blend_w is the TEAM weight.
BEST_BLEND_W = 0.25

# Shots calibration (5-league walk-forward, scripts/shots_calibration_test.py):
# a point-estimate Poisson was confirmed too sharp-tailed (persistent 5-11pt
# overconfidence at 50-90% predicted probability, unmoved by more shrinkage).
# Negative Binomial with this dispersion fixes it (swept 1-15, 3 was the knee).
SHOTS_DISPERSION = 3.0


def load_players() -> pd.DataFrame:
    df = pd.read_parquet(PLAYER_OUTPUT)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["started"] = df["position"] != "Sub"
    return df


def build_team_xg(players: pd.DataFrame, stat_col: str = "xg") -> pd.DataFrame:
    """Aggregate player-match rows to team-match `stat_col` for/against (e.g.
    xG for defence ratings, or `shots` for opponent shot-suppression)."""
    for_col, against_col = f"{stat_col}_for", f"{stat_col}_against"
    tm = players.groupby(["match_id", "date", "league", "team_us", "side"], as_index=False).agg(
        **{for_col: (stat_col, "sum")})
    opp = tm.copy()
    opp["side"] = opp["side"].map({"h": "a", "a": "h"})
    opp = opp.rename(columns={for_col: against_col, "team_us": "opp"})[
        ["match_id", "side", against_col]]
    tm = tm.merge(opp, on=["match_id", "side"])
    return tm.rename(columns={"team_us": "team"})


def _ou_prob_over25(total_mean: float) -> float:
    return float(1.0 - poisson.cdf(2, total_mean))


# Understat position codes -> coarse group. A single league-wide shrinkage
# prior badly overestimates low-volume players (keepers/defenders shrunk
# toward a mean dominated by attackers) - confirmed empirically: it broke
# calibration specifically at low shot-count lines. group_col in
# _decayed_rate() shrinks each player toward their OWN group's mean instead.
POSITION_GROUPS = {
    "GK": "GK",
    "DC": "DEF", "DL": "DEF", "DR": "DEF",
    "DMC": "DMF", "DML": "DMF", "DMR": "DMF",
    "MC": "MID", "ML": "MID", "MR": "MID",
    "AMC": "AM", "AML": "AM", "AMR": "AM",
    "FW": "FWD", "FWL": "FWD", "FWR": "FWD",
}


def _decayed_rate(df: pd.DataFrame, stat_col: str, as_of: pd.Timestamp,
                  decay_xi: float, prior_90s: float, id_col: str = "player_id",
                  group_col: str | None = None) -> tuple[dict, float]:
    """Time-decayed, shrunk per-90 rate for `stat_col`, keyed by `id_col`.
    Shared by attack/defence/shots ratings — same shrinkage-toward-mean
    formula, just a different target stat and (optionally) shrinkage target.

    `group_col`: if given, shrink each player toward THEIR group's mean
    (e.g. position) instead of one global mean — see POSITION_GROUPS above.
    Returns (rates_dict, overall_league_mean) either way; the overall mean is
    only used as a last-resort fallback for a player with no group info."""
    w = np.exp(-decay_xi * (as_of - df["date"]).dt.days.clip(lower=0))
    nineties = df["minutes"] / 90.0
    overall_mean = df[stat_col].sum() / nineties.sum()

    if group_col is not None:
        gg = df.groupby(group_col).agg(_s=(stat_col, "sum"), _m=("minutes", "sum"))
        grp_mean = gg["_s"] / (gg["_m"] / 90.0)
        prior_mean = df[group_col].map(grp_mean).values
    else:
        prior_mean = overall_mean  # scalar broadcasts

    g = pd.DataFrame({"id": df[id_col].values,
                     "w_stat": (w * df[stat_col]).values,
                     "w90": (w * nineties).values,
                     "prior_mean": prior_mean}
                    ).groupby("id").agg(w_stat=("w_stat", "sum"), w90=("w90", "sum"),
                                        prior_mean=("prior_mean", "first"))
    rates = (g["w_stat"] + prior_90s * g["prior_mean"]) / (g["w90"] + prior_90s)
    return rates.to_dict(), overall_mean


def prob_over(rate_per_90: float, minutes_expected: float, line: float,
             dispersion: float | None = None) -> float:
    """P(count > line) for a count stat (shots, SOT, ...) given a per-90 rate
    and expected minutes played.

    `dispersion` (None = Poisson): real shot counts are overdispersed (a
    point-estimate Poisson is confirmed too sharp-tailed - calibration test
    showed persistent overconfidence in the 50-90% probability range that MORE
    shrinkage didn't fix). With a value, uses Negative Binomial instead
    (variance = lam + lam^2/dispersion; smaller dispersion = fatter tails)."""
    lam = rate_per_90 * minutes_expected / 90.0
    if dispersion is None:
        return float(1.0 - poisson.cdf(np.floor(line), lam))
    n, p = dispersion, dispersion / (dispersion + lam)
    return float(1.0 - nbinom.cdf(np.floor(line), n, p))


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
    shots_ratings: dict = field(default_factory=dict, repr=False)
    att_fac: dict = field(default_factory=dict, repr=False)
    def_fac: dict = field(default_factory=dict, repr=False)
    opp_shots_fac: dict = field(default_factory=dict, repr=False)
    lg_team_xg: float = 1.35
    home_mult: float = 1.0
    attack_fallback: float = 0.0
    defence_fallback: float = 0.0
    shots_fallback: float = 0.0
    n_past_matches: int = 0

    @classmethod
    def fit(cls, players: pd.DataFrame, league: str, as_of: pd.Timestamp,
           xa_weight: float = XA_WEIGHT, prior_90s: float = PRIOR_90S,
           blend_w: float = BEST_BLEND_W, shots_prior_90s: float | None = None
           ) -> "LineupModel":
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

        # Attack ratings (time-decayed, shrunk xG+xA per-90).
        past = past.assign(_contrib=past["xg"] + xa_weight * past["xa"])
        m.attack_ratings, m.attack_fallback = _decayed_rate(
            past, "_contrib", as_of, DECAY_XI, prior_90s)

        # Shots ratings, shrunk toward each player's OWN position group's mean
        # (not the whole-league mean — confirmed necessary, see POSITION_GROUPS).
        non_sub = past[past["position"] != "Sub"]
        pos_by_player = (non_sub.groupby("player_id")["position"]
                        .agg(lambda s: s.mode().iat[0])
                        .map(POSITION_GROUPS).fillna("MID"))
        past = past.assign(
            pos_group=past["player_id"].map(pos_by_player).fillna("MID"))
        m.shots_ratings, m.shots_fallback = _decayed_rate(
            past, "shots", as_of, DECAY_XI, shots_prior_90s or prior_90s,
            group_col="pos_group")

        # Opponent shot-suppression: team shots conceded vs league avg.
        past_team_shots = build_team_xg(past, stat_col="shots")
        m.opp_shots_fac = (past_team_shots.groupby("team")["shots_against"].mean()
                          / past_team_shots["shots_against"].mean()).to_dict()

        # Team factors (attack/defence multipliers, league avg xG).
        m.lg_team_xg = past_team_xg["xg_for"].mean()
        m.att_fac = (past_team_xg.groupby("team")["xg_for"].mean() / m.lg_team_xg).to_dict()
        m.def_fac = (past_team_xg.groupby("team")["xg_against"].mean()
                    / past_team_xg["xg_against"].mean()).to_dict()

        # Defence ratings (proxy: team xGA in matches played, minutes-weighted).
        w = np.exp(-DECAY_XI * (as_of - past["date"]).dt.days.clip(lower=0))
        nineties = past["minutes"] / 90.0
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

    def predict_player_shots(self, player_id, opponent_team: str,
                             minutes_expected: float, line: float,
                             dispersion: float | None = SHOTS_DISPERSION) -> float:
        """P(player's shots in this match > `line`), from the player's own
        decayed shot rate adjusted for the opponent's shot-suppression.

        "Team playing style" is already baked into the player's own rate
        (a winger on a possession-heavy team already shows a higher decayed
        rate) — no separate style factor needed. Rest days / fitness are NOT
        modeled (no data source for either); if you have a specific
        adjustment, scale `minutes_expected` or the returned rate yourself.
        `dispersion`: see prob_over() — defaults to the confirmed NB fit;
        pass None for plain Poisson.
        """
        rate = self.shots_ratings.get(player_id, self.shots_fallback)
        rate *= self.opp_shots_fac.get(opponent_team, 1.0)
        return prob_over(rate, minutes_expected, line, dispersion)


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


if __name__ == "__main__":
    # Self-check: player-shots probability should behave sanely — more
    # expected minutes -> higher P(over), and a known high-shot-volume
    # attacker should clear a modest line more often than not.
    players = load_players()
    model = LineupModel.fit(players, "E0", pd.Timestamp("2024-01-01"))
    top_shooter = max(model.shots_ratings, key=model.shots_ratings.get)
    rate = model.shots_ratings[top_shooter]
    p_60 = model.predict_player_shots(top_shooter, "Everton", 60, 1.5)
    p_90 = model.predict_player_shots(top_shooter, "Everton", 90, 1.5)
    print(f"top shot-rate player {top_shooter}: {rate:.2f} shots/90")
    print(f"P(shots > 1.5 | 60 min) = {p_60:.3f}   P(shots > 1.5 | 90 min) = {p_90:.3f}")
    assert 0 <= p_60 <= 1 and 0 <= p_90 <= 1
    assert p_90 > p_60, "more minutes should raise P(over) for a fixed line"
    print("OK")
