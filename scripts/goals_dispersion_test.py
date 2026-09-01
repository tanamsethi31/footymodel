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

    print(evals.groupby("league").size())
