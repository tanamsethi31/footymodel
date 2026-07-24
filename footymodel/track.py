"""Paper-trade tracker — score logged recommendations against real results.

Reads data/processed/paper_trades.csv (written by recommend.py), matches each
bet to its finished result in the dataset, and reports running yield, win rate,
and CLV. This is how you watch the live verdict build before risking money.

Usage:
    python -m footymodel.track
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import load
from .recommend import PAPER_LOG


def _result_total(df: pd.DataFrame) -> dict:
    """(date, league, home, away) -> total goals, for finished matches."""
    out = {}
    for r in df.itertuples(index=False):
        out[(pd.Timestamp(r.date).normalize(), r.league, r.home_team, r.away_team)] = \
            (r.fthg + r.ftag) if pd.notna(r.fthg) and pd.notna(r.ftag) else None
    return out


def track(path=PAPER_LOG) -> None:
    if not path.exists():
        print("No paper_trades.csv yet — run the recommender first.")
        return
    bets = pd.read_csv(path, parse_dates=["date"])
    results = _result_total(load())

    graded = []
    for r in bets.itertuples(index=False):
        key = (pd.Timestamp(r.date).normalize(), r.league, r.home, r.away)
        tot = results.get(key)
        if tot is None:
            continue  # not played yet (or not in dataset)
        won = (tot > 2.5) if r.market == "over25" else (tot < 2.5)
        stake = getattr(r, "stake", 1.0)
        graded.append({"won": won, "stake": stake,
                       "profit": stake * (r.odds - 1) if won else -stake})
    g = pd.DataFrame(graded)

    n_total, n_graded = len(bets), len(g)
    print(f"Paper trades logged : {n_total}")
    print(f"Graded (finished)   : {n_graded}   pending: {n_total - n_graded}")
    if g.empty:
        print("Nothing graded yet — results not in the dataset. Re-run "
              "`python -m footymodel.data` after matches are played.")
        return
    staked, profit = g["stake"].sum(), g["profit"].sum()
    print(f"Win rate            : {g['won'].mean()*100:.1f}%")
    print(f"Staked / returned   : {staked:.2f}u / {staked + profit:.2f}u")
    print(f"Profit              : {profit:+.2f}u")
    print(f"Running YIELD       : {profit / staked * 100:+.2f}%  "
          f"(watch this vs the -2.6% best-price backtest)")


if __name__ == "__main__":
    track()
