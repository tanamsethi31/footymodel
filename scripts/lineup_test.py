"""Does lineup info improve O/U prediction? Strengthened model + blend sweep.

Runs the walk-forward test (raw expected totals), scale-calibrates each model,
sweeps the team/lineup blend weight, and reports Brier/log-loss/accuracy plus a
paired significance test of the best blend vs the team baseline.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from scipy.stats import poisson

from footymodel.players import accuracy_test

XA_WEIGHT = 0.5
PRIOR_90S = 6.0
LEAGUES = sys.argv[1].split(",") if len(sys.argv) > 1 else ["E0"]

frames = []
for lg in LEAGUES:
    rl = accuracy_test(test_start="2022-07-01", league=lg,
                       xa_weight=XA_WEIGHT, prior_90s=PRIOR_90S)
    rl["league"] = lg
    print(f"  {lg}: {len(rl)} matches")
    frames.append(rl)
r = pd.concat(frames, ignore_index=True)
y = r["over_won"].astype(int).values
print(f"\nEvaluated {len(r)} matches across {LEAGUES} | xa_weight={XA_WEIGHT} prior_90s={PRIOR_90S}\n")

# Scale-calibrate PER LEAGUE (scoring rates differ) so mean predicted P(over)
# matches that league's empirical over-rate, then pool for the significance test.
def calibrate_league(raw, target_mean):
    lo, hi = 0.5, 1.5
    for _ in range(40):
        s = (lo + hi) / 2
        mp = (1 - poisson.cdf(2, raw * s)).mean()
        if mp > target_mean: hi = s
        else: lo = s
    return raw * (lo + hi) / 2

team_t = np.zeros(len(r))
line_t = np.zeros(len(r))
for lg in LEAGUES:
    m = (r["league"] == lg).values
    target = y[m].mean()
    team_t[m] = calibrate_league(r.loc[m, "exp_team"].values, target)
    line_t[m] = calibrate_league(r.loc[m, "exp_line"].values, target)


def metrics(total):
    p = np.clip(1 - poisson.cdf(2, total), 1e-9, 1 - 1e-9)
    brier = np.mean((p - y) ** 2)
    ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    fav = np.where(p >= 0.5, y, 1 - y).mean()
    return brier, ll, fav, (p - y) ** 2  # last: per-match sq error for sig test


print(f"{'model':>12} {'Brier':>8} {'LogLoss':>8} {'FavAcc':>7}")
print("-" * 40)
bt, llt, fat, se_team = metrics(team_t)
print(f"{'team':>12} {bt:>8.4f} {llt:>8.4f} {fat*100:>6.1f}%")
best = (None, 1.0, bt)
for w in [0.75, 0.6, 0.5, 0.4, 0.25, 0.0]:
    blend = w * team_t + (1 - w) * line_t
    b, ll, fa, se = metrics(blend)
    tag = "lineup-only" if w == 0 else f"blend w={w}"
    print(f"{tag:>12} {b:>8.4f} {ll:>8.4f} {fa*100:>6.1f}%")
    if b < best[2]:
        best = (se, w, b)

# Significance of best blend vs team (paired diff of squared errors)
se_best, w_best, b_best = best
if se_best is not None:
    d = se_team - se_best  # >0 means blend better
    t = d.mean() / (d.std() / np.sqrt(len(d)))
    print("-" * 40)
    print(f"Best: blend w={w_best} (team weight). Brier {b_best:.4f} vs team {bt:.4f}")
    print(f"Paired improvement t-stat: {t:.2f}  "
          f"({'significant' if abs(t) > 2 else 'NOT significant'})")
else:
    print("\nNo blend beat the team baseline.")
