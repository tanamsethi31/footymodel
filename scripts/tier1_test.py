"""Tier-1 test: does shot-xG-blended fitting improve O/U yield at best price?

Builds walk-forward evaluations with a goals/shot-xG blend, then re-prices the
O/U value bets at market MAX odds. Compares against the goals-only baseline.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from footymodel import config
from footymodel.data import load, PROCESSED_DIR
from footymodel.strategy import build_evaluations

BLEND = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
TEST_START = "2022-07-01"
EDGE = 0.05
EVALS_PATH = PROCESSED_DIR / f"evals_blend{int(BLEND*100)}.parquet"

df = load()
if EVALS_PATH.exists():
    evals = pd.read_parquet(EVALS_PATH)
    print(f"Loaded cached evals (blend={BLEND}): {len(evals)} selections")
else:
    print(f"Building evals with blend={BLEND} (goals={BLEND:g}/shot-xG={1-BLEND:g})...")
    evals = build_evaluations(df, config.DEFAULT_LEAGUES, TEST_START, blend=BLEND)
    evals.to_parquet(EVALS_PATH, index=False)
    print(f"Saved -> {EVALS_PATH}")

evals = evals[evals["market"].isin(["over25", "under25"])].copy()
mx = df[["date", "league", "home_team", "away_team",
         "odds_over25_max", "odds_under25_max"]]
evals = evals.merge(mx, left_on=["date", "league", "home", "away"],
                    right_on=["date", "league", "home_team", "away_team"], how="left")
evals["odds_maxclose"] = evals.apply(
    lambda r: r[f"odds_{r['market']}_max"], axis=1)


def sim(odds_col, label):
    e = evals.dropna(subset=[odds_col, "odds_close"]).copy()
    odds = e[odds_col]
    ev = e["model_p"] * odds - 1.0
    keep = odds.between(1.3, 8.0) & (ev > EDGE)
    b = e[keep]
    if b.empty:
        print(f"{label:28s} no bets"); return
    profit = np.where(b["won"], b[odds_col] - 1.0, -1.0)
    y = profit.sum() / len(b) * 100
    print(f"{label:28s} n={len(b):5d}  yield={y:+6.2f}%  win={b['won'].mean()*100:4.1f}%")


print(f"\nO/U strategy — blend={BLEND} (goals+shot-xG), edge {EDGE}")
print("=" * 60)
sim("odds_close", "avg close")
sim("odds_maxclose", "MAX close (best price)")
print("=" * 60)
print("Compare MAX-close vs goals-only baseline (-2.56%).")
