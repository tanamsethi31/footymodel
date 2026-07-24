"""Best-price (line-shopping) test for the O/U strategy.

Reuses the cached walk-forward evaluations (model probs + outcomes) and re-prices
the SAME bets at the market MAXIMUM odds instead of the average, to see whether
line shopping turns the Over/Under strategy profitable. No model re-fit needed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from footymodel.data import load, PROCESSED_DIR
from footymodel.strategy import remove_margin

EDGE = 0.05
evals = pd.read_parquet(PROCESSED_DIR / "evals_main.parquet")
evals = evals[evals["market"].isin(["over25", "under25"])].copy()

# Merge max odds (open + close) onto evals, per market, by fixture key.
m = load()[["date", "league", "home_team", "away_team",
            "odds_over25_max", "odds_under25_max",
            "odds_over25_maxopen", "odds_under25_maxopen"]]
evals = evals.merge(m, left_on=["date", "league", "home", "away"],
                    right_on=["date", "league", "home_team", "away_team"], how="left")

def max_odds(row, when):  # when in {"max","maxopen"}
    col = f"odds_{row['market']}_{when}"
    return row[col]

evals["odds_maxclose"] = evals.apply(lambda r: max_odds(r, "max"), axis=1)
evals["odds_maxopen"] = evals.apply(lambda r: max_odds(r, "maxopen"), axis=1)


def simulate(odds_col, ref_close_col, label):
    e = evals.dropna(subset=[odds_col, ref_close_col]).copy()
    odds = e[odds_col]
    # fair from the same source's two-way market where available; else raw implied
    ev = e["model_p"] * odds - 1.0
    keep = odds.between(1.3, 8.0) & (ev > EDGE)
    b = e[keep].copy()
    if b.empty:
        print(f"{label:22s}  no bets"); return
    b["odds"] = odds[keep]
    b["profit"] = np.where(b["won"], b["odds"] - 1.0, -1.0)
    # CLV vs the AVERAGE closing line (our consistent sharp-ish reference)
    b["clv"] = b["odds"] / b[ref_close_col] - 1.0
    y = b["profit"].sum() / len(b) * 100
    print(f"{label:22s}  n={len(b):5d}  yield={y:+6.2f}%  "
          f"avgOdds={b['odds'].mean():.3f}  win={b['won'].mean()*100:4.1f}%  "
          f"CLVvsAvgClose={b['clv'].mean()*100:+5.2f}%")


print("O/U strategy, edge 5% — price execution comparison")
print("=" * 78)
simulate("odds_close", "odds_close", "AVG close (baseline)")
simulate("odds_open", "odds_close", "AVG open (baseline)")
simulate("odds_maxclose", "odds_close", "MAX close (best price)")
simulate("odds_maxopen", "odds_close", "MAX open (best price)")
print("=" * 78)
print("Yield = realized ROI at that price. MAX = best available across books.")
