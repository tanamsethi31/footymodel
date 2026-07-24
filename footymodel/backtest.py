"""Phase 3 — value detection + walk-forward backtest (the go/no-go gate).

For each fixture we:
  1. fit the Dixon-Coles model on matches *strictly before* the fixture date
     (no lookahead), refitting once per matchday for efficiency;
  2. read the model's market probabilities;
  3. compare against the bookmaker closing odds. A bet is placed when the
     model's expected value  EV = p * odds - 1  exceeds an edge threshold.

We stake flat 1 unit (Kelly is Phase 5) and report yield (profit / staked).

Two outputs, both essential:
  * betting performance — did value bets make money vs the closing line?
  * calibration — when the model says 60%, does it happen ~60%? A model can be
    "accurate" yet miscalibrated and unprofitable; this is the real gate.

Usage:
    python -m footymodel.backtest --leagues E0 --test-start 2022-07-01 --edge 0.05
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from . import config
from .data import load
from .model import DixonColes

# Each market: (model prob key, odds column, outcome function on a match row).
MARKETS = {
    "home":   ("p_home",    "odds_h",       lambda r: r.fthg > r.ftag),
    "draw":   ("p_draw",    "odds_d",       lambda r: r.fthg == r.ftag),
    "away":   ("p_away",    "odds_a",       lambda r: r.fthg < r.ftag),
    "over25": ("p_over25",  "odds_over25",  lambda r: (r.fthg + r.ftag) > 2.5),
    "under25":("p_under25", "odds_under25", lambda r: (r.fthg + r.ftag) < 2.5),
}


def remove_margin(odds: np.ndarray) -> np.ndarray:
    """Multiplicative (proportional) margin removal -> fair probabilities.

    Simple and standard. Shin / power methods (which handle favourite-longshot
    bias better) are a documented future improvement.
    """
    raw = 1.0 / odds
    return raw / raw.sum()


def walk_forward(df: pd.DataFrame, league: str, test_start: str,
                 xi: float = 0.0018, edge: float = 0.05,
                 min_train: int = 200, min_odds: float = 1.2,
                 max_odds: float = 15.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the walk-forward backtest for one league.

    Returns (bets, predictions):
      bets        — one row per placed value bet (for P&L / yield).
      predictions — one row per (fixture, market) evaluated (for calibration).
    """
    league_df = df[df["league"] == league].sort_values("date").reset_index(drop=True)
    test_start = pd.Timestamp(test_start)
    test_dates = sorted(league_df.loc[league_df["date"] >= test_start, "date"].unique())

    bets, preds = [], []
    for d in test_dates:
        d = pd.Timestamp(d)
        train = league_df[league_df["date"] < d]
        if len(train) < min_train:
            continue
        model = DixonColes(xi=xi).fit(train, ref_date=d)
        fixtures = league_df[league_df["date"] == d]

        for r in fixtures.itertuples(index=False):
            if r.home_team not in model.attack or r.away_team not in model.attack:
                continue  # newly promoted team with no history yet
            try:
                mp = model.predict_markets(r.home_team, r.away_team)
            except KeyError:
                continue

            for market, (pkey, ocol, outcome_fn) in MARKETS.items():
                odds = getattr(r, ocol)
                if pd.isna(odds) or not (min_odds <= odds <= max_odds):
                    continue
                p = mp[pkey]
                won = bool(outcome_fn(r))
                preds.append({"date": d, "league": league, "market": market,
                              "p": p, "won": won})

                ev = p * odds - 1.0
                if ev > edge:
                    profit = (odds - 1.0) if won else -1.0
                    bets.append({
                        "date": d, "league": league,
                        "home": r.home_team, "away": r.away_team,
                        "market": market, "odds": float(odds),
                        "model_p": p, "fair_p_raw": 1.0 / odds,
                        "ev": ev, "won": won, "profit": profit,
                    })

    return pd.DataFrame(bets), pd.DataFrame(preds)


def summarize_bets(bets: pd.DataFrame) -> None:
    if bets.empty:
        print("No value bets placed at this edge threshold.")
        return
    n = len(bets)
    staked = float(n)
    profit = bets["profit"].sum()
    print(f"Value bets   : {n}")
    print(f"Win rate     : {bets['won'].mean() * 100:5.1f}%   (NOT the target — yield is)")
    print(f"Avg odds     : {bets['odds'].mean():.2f}   avg model edge (EV): {bets['ev'].mean() * 100:.1f}%")
    print(f"Staked       : {staked:.0f} u   Returned: {staked + profit:.1f} u")
    print(f"Profit       : {profit:+.2f} u")
    print(f"YIELD (ROI)  : {profit / staked * 100:+.2f}%   <-- the number that matters")
    print("\n  By market:")
    for mk, g in bets.groupby("market"):
        y = g["profit"].sum() / len(g) * 100
        print(f"    {mk:8s} n={len(g):4d}  win={g['won'].mean()*100:4.0f}%  yield={y:+6.1f}%")


def calibration_table(preds: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """Reliability table over ALL evaluated selections (not just bets)."""
    if preds.empty:
        return pd.DataFrame()
    p = preds.copy()
    p["bucket"] = (p["p"] * bins).clip(0, bins - 1).astype(int)
    rows = []
    for b, g in p.groupby("bucket"):
        rows.append({"prob_range": f"{b/bins:.1f}-{(b+1)/bins:.1f}",
                     "n": len(g), "pred_mean": g["p"].mean(),
                     "actual": g["won"].mean(),
                     "gap": g["won"].mean() - g["p"].mean()})
    return pd.DataFrame(rows)


def _benchmark_yield(preds: pd.DataFrame, df: pd.DataFrame, league: str) -> None:
    """Naive baseline: flat-bet the bookmaker favourite every match. Should
    land near -margin (~-5%); our model must beat this to have any edge."""
    league_df = df[df["league"] == league]
    sub = league_df[league_df["date"].isin(preds["date"].unique())]
    profit = n = 0
    for r in sub.itertuples(index=False):
        odds = [r.odds_h, r.odds_d, r.odds_a]
        if any(pd.isna(o) for o in odds):
            continue
        pick = int(np.argmin(odds))  # shortest price = favourite
        won = [r.fthg > r.ftag, r.fthg == r.ftag, r.fthg < r.ftag][pick]
        profit += (odds[pick] - 1.0) if won else -1.0
        n += 1
    if n:
        print(f"\nBaseline (bet favourite every match): yield {profit/n*100:+.2f}% over {n} bets")


def run(leagues, test_start, xi, edge, df=None):
    if df is None:
        df = load()
    all_bets, all_preds = [], []
    for lg in leagues:
        print(f"\n{'='*64}\n{lg} — {config.LEAGUES.get(lg, lg)}\n{'='*64}")
        bets, preds = walk_forward(df, lg, test_start, xi=xi, edge=edge)
        summarize_bets(bets)
        _benchmark_yield(preds, df, lg)
        if not preds.empty:
            print("\n  Calibration (all evaluated selections):")
            print(calibration_table(preds).to_string(
                index=False, float_format=lambda v: f"{v:.3f}"))
        all_bets.append(bets)
        all_preds.append(preds)

    bets = pd.concat(all_bets, ignore_index=True) if all_bets else pd.DataFrame()
    preds = pd.concat(all_preds, ignore_index=True) if all_preds else pd.DataFrame()
    if len(leagues) > 1:
        print(f"\n{'#'*64}\nPOOLED ACROSS ALL LEAGUES\n{'#'*64}")
        summarize_bets(bets)
        if not preds.empty:
            print("\n  Pooled calibration:")
            print(calibration_table(preds).to_string(
                index=False, float_format=lambda v: f"{v:.3f}"))
    return bets, preds


def main():
    p = argparse.ArgumentParser(description="Walk-forward value backtest.")
    p.add_argument("--leagues", nargs="+", default=config.DEFAULT_LEAGUES)
    p.add_argument("--test-start", default="2022-07-01",
                   help="Bet only on/after this date; earlier matches train the model.")
    p.add_argument("--xi", type=float, default=0.0018, help="Time-decay rate/day")
    p.add_argument("--edge", type=float, default=0.05, help="Min EV to place a bet")
    args = p.parse_args()
    run(args.leagues, args.test_start, args.xi, args.edge)


if __name__ == "__main__":
    main()
