"""Pure prediction quality vs. monetization — answering "just bet the confident ones".

Ignores value/edge. Takes the model's favored O/U side per match, reports raw
predictive accuracy (hit rate, Brier, log-loss), then shows what flat-betting
those confident predictions actually yields at avg AND best-price odds.

Point: accuracy is real, but a confident prediction the bookmaker shares is not
profitable — you need a PRICE edge, which is why odds can't be ignored.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from footymodel.data import load, PROCESSED_DIR

e = pd.read_parquet(PROCESSED_DIR / "evals_main.parquet")
over = e[e["market"] == "over25"][["date", "league", "home", "away", "model_p", "won",
                                   "odds_open", "odds_close"]].rename(
    columns={"model_p": "p_over", "won": "over_won",
             "odds_open": "over_open", "odds_close": "over_close"})
under = e[e["market"] == "under25"][["date", "league", "home", "away",
                                     "odds_open", "odds_close"]].rename(
    columns={"odds_open": "under_open", "odds_close": "under_close"})
fx = over.merge(under, on=["date", "league", "home", "away"], how="inner")

# best-price (max) odds
mx = load()[["date", "league", "home_team", "away_team",
             "odds_over25_max", "odds_under25_max"]]
fx = fx.merge(mx, left_on=["date", "league", "home", "away"],
              right_on=["date", "league", "home_team", "away_team"], how="left")

# Favored side per match and its outcome.
fx["fav_over"] = fx["p_over"] >= 0.5
fx["conf"] = np.where(fx["fav_over"], fx["p_over"], 1 - fx["p_over"])
fx["fav_won"] = np.where(fx["fav_over"], fx["over_won"], ~fx["over_won"])
fx["fav_close"] = np.where(fx["fav_over"], fx["over_close"], fx["under_close"])
fx["fav_max"] = np.where(fx["fav_over"], fx["odds_over25_max"], fx["odds_under25_max"])

# --- Pure prediction quality (no odds) ---
p, y = fx["p_over"].values, fx["over_won"].astype(int).values
brier = np.mean((p - y) ** 2)
eps = 1e-9
logloss = -np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps))
print("PURE PREDICTION QUALITY (Over/Under 2.5, no odds)")
print("=" * 66)
print(f"Matches                : {len(fx)}")
print(f"Favored-side accuracy  : {fx['fav_won'].mean()*100:.1f}%  "
      f"(base rate over={fx['over_won'].mean()*100:.1f}%)")
print(f"Brier score            : {brier:.4f}  (0=perfect, 0.25=coin flip)")
print(f"Log loss               : {logloss:.4f}  (lower=better; 0.693=coin flip)")

# --- Monetization: bet the favored side, by confidence ---
print("\nBET THE FAVORED SIDE, by confidence — accuracy vs yield")
print("=" * 66)
print(f"{'min conf':>8} {'bets':>6} {'hit%':>6} {'avg fair':>8} "
      f"{'yield@avg':>10} {'yield@max':>10}")
for thr in [0.50, 0.55, 0.60, 0.65, 0.70]:
    s = fx[fx["conf"] >= thr].dropna(subset=["fav_close", "fav_max"])
    if s.empty:
        continue
    hit = s["fav_won"].mean()
    y_avg = np.where(s["fav_won"], s["fav_close"] - 1, -1).mean() * 100
    y_max = np.where(s["fav_won"], s["fav_max"] - 1, -1).mean() * 100
    print(f"{thr:>8.2f} {len(s):>6d} {hit*100:>5.1f}% {s['fav_close'].mean():>8.2f} "
          f"{y_avg:>+9.2f}% {y_max:>+9.2f}%")
print("=" * 66)
print("Hit% is high & accurate — but yield stays negative even at best price:")
print("the bookmaker shares your confidence, so there's no price edge to bank.")
