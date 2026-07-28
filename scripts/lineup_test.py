"""Does lineup info improve O/U prediction? Team vs half-lineup (attack-only)
vs full-lineup (attack+defence from the actual starting XI).

Runs the walk-forward test (raw expected totals), scale-calibrates each model
PER LEAGUE, sweeps blend weights against the team baseline for both the
half-lineup and full-lineup models, and reports Brier/log-loss/accuracy plus a
paired significance test of the best model vs the team baseline.
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


def calibrate_league(raw, target_mean):
    lo, hi = 0.5, 1.5
    for _ in range(40):
        s = (lo + hi) / 2
        mp = (1 - poisson.cdf(2, raw * s)).mean()
        if mp > target_mean: hi = s
        else: lo = s
    return raw * (lo + hi) / 2


team_t = np.zeros(len(r))
half_t = np.zeros(len(r))
full_t = np.zeros(len(r))
for lg in LEAGUES:
    m = (r["league"] == lg).values
    target = y[m].mean()
    team_t[m] = calibrate_league(r.loc[m, "exp_team"].values, target)
    half_t[m] = calibrate_league(r.loc[m, "exp_line"].values, target)
    full_t[m] = calibrate_league(r.loc[m, "exp_full"].values, target)


def metrics(total):
    p = np.clip(1 - poisson.cdf(2, total), 1e-9, 1 - 1e-9)
    brier = np.mean((p - y) ** 2)
    ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    fav = np.where(p >= 0.5, y, 1 - y).mean()
    return brier, ll, fav, (p - y) ** 2


bt, llt, fat, se_team = metrics(team_t)
print(f"{'model':>14} {'Brier':>8} {'LogLoss':>8} {'FavAcc':>7}")
print("-" * 42)
print(f"{'team':>14} {bt:>8.4f} {llt:>8.4f} {fat*100:>6.1f}%")

best = (se_team, "team (baseline)", bt)
for name, line_est in [("half (attack)", half_t), ("full (att+def)", full_t)]:
    for w in [1.0, 0.75, 0.6, 0.5, 0.4, 0.25, 0.0]:
        blend = w * team_t + (1 - w) * line_est
        b, ll, fa, se = metrics(blend)
        tag = f"{name} w={w}"
        print(f"{tag:>14} {b:>8.4f} {ll:>8.4f} {fa*100:>6.1f}%")
        if b < best[2]:
            best = (se, tag, b)

se_best, tag_best, b_best = best
print("-" * 42)
if tag_best == "team (baseline)":
    print("No lineup model beat the team baseline.")
else:
    d = se_team - se_best
    t = d.mean() / (d.std() / np.sqrt(len(d)))
    print(f"Best: {tag_best}. Brier {b_best:.4f} vs team {bt:.4f}")
    print(f"Paired improvement t-stat: {t:.2f}  "
          f"({'significant' if abs(t) > 2 else 'NOT significant'})")
