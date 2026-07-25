"""Does lineup-aware attack beat team-average attack at predicting O/U?

Runs the walk-forward accuracy test and reports Brier score, log-loss, and
favored-side accuracy for the lineup model vs the team-level baseline on the
SAME matches. Lower Brier/log-loss = better predictions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from footymodel.players import accuracy_test

r = accuracy_test(test_start="2022-07-01", league="E0")
print(f"Evaluated {len(r)} matches (E0, test period).\n")
y = r["over_won"].astype(int).values
eps = 1e-9


def metrics(p):
    p = np.clip(p, eps, 1 - eps)
    brier = np.mean((p - y) ** 2)
    logloss = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    fav = np.where(p >= 0.5, y, 1 - y).mean()  # favored-side accuracy
    return brier, logloss, fav


print(f"{'model':>10} {'Brier':>8} {'LogLoss':>8} {'FavAcc':>8}")
print("-" * 38)
for name, col in [("team", "p_over_team"), ("lineup", "p_over_lineup")]:
    b, ll, fa = metrics(r[col].values)
    print(f"{name:>10} {b:>8.4f} {ll:>8.4f} {fa*100:>7.1f}%")
print("-" * 38)
bt, _, _ = metrics(r["p_over_team"].values)
bl, _, _ = metrics(r["p_over_lineup"].values)
print(f"\nLineup vs team Brier: {bl:.4f} vs {bt:.4f}  "
      f"({'BETTER' if bl < bt else 'worse'} by {abs(bl-bt):.4f})")
print("Coin-flip Brier = 0.25. Lower is better. Improvement here = lineup info helps.")
