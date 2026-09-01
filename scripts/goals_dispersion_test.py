"""Goals-level Negative-Binomial dispersion test. LineupModel.predict()'s
Over/Under 2.5 probability (_ou_prob_over25) uses a plain Poisson - the shots
submodel already found Poisson too sharp-tailed for count data and fixed it
with an NB dispersion (SHOTS_DISPERSION=3.0, scripts/shots_calibration_test.py).
This runs the identical test on the goals model: does the same fix apply?

Two-stage like shots_calibration_test.py: evaluate() does the expensive
walk-forward once (via players.accuracy_test(), unchanged), caching the raw
exp_team/exp_full per match. simulate() cheaply sweeps Poisson vs NB
dispersion on the cached values, printing Brier + calibration table per
league and pooled. See
docs/superpowers/specs/2026-09-01-goals-dispersion-test-design.md for the
go/no-go gate. Investigative only - does not touch LineupModel/players.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson

from footymodel.backtest import calibration_table
from footymodel.players import BEST_BLEND_W, accuracy_test

LEAGUES = sys.argv[1].split(",") if len(sys.argv) > 1 else ["E0", "SP1", "D1", "I1", "F1"]
TEST_START = "2022-07-01"
MIN_TRAIN_ROWS = 5000
DISPERSIONS = [None, 1, 2, 3, 4, 5, 6, 8, 10, 15]
CACHE = Path(__file__).resolve().parent.parent / "data" / "processed" / "goals_eval_cache.parquet"


def evaluate(leagues: list[str]) -> pd.DataFrame:
    frames = []
    for lg in leagues:
        print(f"  evaluating {lg} ...", flush=True)
        r = accuracy_test(test_start=TEST_START, league=lg, min_train_rows=MIN_TRAIN_ROWS)
        r["league"] = lg
        print(f"    {len(r)} matches", flush=True)
        frames.append(r)
    return pd.concat(frames, ignore_index=True)


def calibrate_league(raw: np.ndarray, target_mean: float) -> np.ndarray:
    """Binary-search a multiplicative scale on the raw expected total so the
    Poisson-implied mean P(over) matches the league's actual over-rate -
    isolates the mean-bias question from the dispersion (tail-shape)
    question tested below. Local copy of lineup_test.py's own helper -
    matches this project's existing precedent of each sweep script keeping
    its own small conversion logic rather than sharing one across two call
    sites."""
    lo, hi = 0.5, 1.5
    for _ in range(40):
        s = (lo + hi) / 2
        mp = (1 - poisson.cdf(2, raw * s)).mean()
        if mp > target_mean:
            hi = s
        else:
            lo = s
    return raw * (lo + hi) / 2


def simulate(evals: pd.DataFrame, dispersion: float | None) -> tuple[float, np.ndarray]:
    """Scale-calibrate per league, convert to a probability at this
    dispersion, print Brier + calibration table per league and pooled.
    Returns (pooled_brier, pooled_squared_error) for the significance check."""
    all_p, all_y = [], []
    tag = "Poisson" if dispersion is None else f"NB(disp={dispersion})"
    for lg, g in evals.groupby("league"):
        y = g["over_won"].astype(int).values
        exp_blend = BEST_BLEND_W * g["exp_team"].values + (1 - BEST_BLEND_W) * g["exp_full"].values
        scaled = calibrate_league(exp_blend, y.mean())
        if dispersion is None:
            p = np.clip(1 - poisson.cdf(2, scaled), 1e-9, 1 - 1e-9)
        else:
            n, prm = dispersion, dispersion / (dispersion + scaled)
            p = np.clip(1 - nbinom.cdf(2, n, prm), 1e-9, 1 - 1e-9)
        brier = np.mean((p - y) ** 2)
        print(f"=== {lg} [{tag}] — n={len(p)} — Brier {brier:.4f} ===")
        print(calibration_table(pd.DataFrame({"p": p, "won": y}))
              .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
        all_p.append(p)
        all_y.append(y)

    p_all = np.concatenate(all_p)
    y_all = np.concatenate(all_y)
    brier_pooled = np.mean((p_all - y_all) ** 2)
    print(f"--- POOLED [{tag}] — n={len(p_all)} — Brier {brier_pooled:.4f} ---")
    print(calibration_table(pd.DataFrame({"p": p_all, "won": y_all}))
          .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print()
    return brier_pooled, (p_all - y_all) ** 2


if __name__ == "__main__":
    if CACHE.exists():
        evals = pd.read_parquet(CACHE)
        print(f"Loaded cached evaluations: {len(evals)} rows")
    else:
        print("Evaluating (walk-forward, per matchday)...")
        evals = evaluate(LEAGUES)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        evals.to_parquet(CACHE, index=False)
        print(f"Saved -> {CACHE}  ({len(evals)} rows)")

    results = {d: simulate(evals, d) for d in DISPERSIONS}

    baseline_brier, baseline_se = results[None]
    best_d = min((d for d in DISPERSIONS if d is not None), key=lambda d: results[d][0])
    best_brier, best_se = results[best_d]
    diff = baseline_se - best_se
    t = diff.mean() / (diff.std() / np.sqrt(len(diff)))
    print("=" * 64)
    print(f"Poisson baseline pooled Brier: {baseline_brier:.4f}")
    print(f"Best NB(disp={best_d}) pooled Brier: {best_brier:.4f}")
    print(f"Paired t-stat: {t:.2f}  ({'significant' if abs(t) > 2 else 'NOT significant'})")
