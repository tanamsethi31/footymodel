# Goals-Level NB-Dispersion Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find out whether `LineupModel`'s goals-level Over/Under 2.5 probability — which still uses a plain Poisson — suffers from the same overdispersion the shots submodel already found and fixed, by running the identical Negative-Binomial dispersion sweep across the big-5 leagues.

**Architecture:** A new standalone, read-only investigation script, `scripts/goals_dispersion_test.py`, mirroring `scripts/shots_calibration_test.py`'s two-stage cache-then-sweep pattern: `evaluate()` runs the expensive walk-forward once (via `players.py`'s existing `accuracy_test()`, unchanged) and caches raw `exp_team`/`exp_full` per match; `simulate()` cheaply re-applies scale-calibration + a candidate dispersion value and prints Brier/calibration/significance numbers. No production code (`players.py`, `engine.py`, `run_all.py`) is touched — this produces evidence only.

**Tech Stack:** Python 3.11 (repo venv: `.venv/bin/python`), pandas/numpy/scipy (`nbinom`, `poisson`) — all already dependencies, no new packages.

See spec: `docs/superpowers/specs/2026-09-01-goals-dispersion-test-design.md`

---

### Task 1: Build the walk-forward cache

**Files:**
- Create: `scripts/goals_dispersion_test.py`

- [ ] **Step 1: Write `evaluate()` and the cache-building `__main__` block**

Create `scripts/goals_dispersion_test.py`:

```python
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
```

- [ ] **Step 2: Run it and confirm the walk-forward completes and caches**

Run: `.venv/bin/python scripts/goals_dispersion_test.py`
Expected: prints "evaluating E0 ...", "evaluating SP1 ...", etc. for all 5 leagues, each with a nonzero match count, ends with "Saved -> .../goals_eval_cache.parquet (N rows)" and a per-league size breakdown. This may take a few minutes (5 leagues' worth of walk-forward `LineupModel.fit()` calls) — that cost is paid once, here.

- [ ] **Step 3: Confirm the cache is reused on a second run**

Run: `.venv/bin/python scripts/goals_dispersion_test.py`
Expected: prints "Loaded cached evaluations: N rows" (same N as Step 2) instead of re-running the walk-forward — confirms the cache actually short-circuits re-fitting.

- [ ] **Step 4: Commit**

```bash
git add scripts/goals_dispersion_test.py
git commit -m "feat: cache goals-level walk-forward for NB-dispersion test"
```

---

### Task 2: Sweep dispersion, report calibration + significance

**Files:**
- Modify: `scripts/goals_dispersion_test.py`

- [ ] **Step 1: Add `calibrate_league()`, `simulate()`, and the sweep + significance report**

In `scripts/goals_dispersion_test.py`, just above the `if __name__ == "__main__":` block, add:

```python
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
```

Then find:

```python
    print(evals.groupby("league").size())
```

(Task 1's own sanity-check line, no longer needed) and replace it with:

```python
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
```

- [ ] **Step 2: Run the full sweep for real**

Run: `.venv/bin/python scripts/goals_dispersion_test.py`
Expected: since the cache from Task 1 already exists, this loads instantly ("Loaded cached evaluations..."), then prints a Brier + calibration table for each of the 10 dispersion values (`None`, `1`, `2`, ..., `15`) — per league and pooled — ending with the summary block comparing the Poisson baseline to the best NB candidate and the paired t-stat.

- [ ] **Step 3: Evaluate against the go/no-go gate**

Per the design spec: only worth adopting if (a) pooled Brier improves vs Poisson, (b) the paired t-stat > 2, and (c) every individual league's Brier improves or is neutral, not just the pooled average. Read the printed per-league Brier lines for the best dispersion value found in Step 2 and check all three conditions by hand.

- [ ] **Step 4: Commit**

```bash
git add scripts/goals_dispersion_test.py
git commit -m "feat: NB-dispersion sweep + significance check for goals model"
```

---

## Post-plan verification

The real output of this plan is the printed sweep report from Task 2 Step 2, not a code artifact — read it and apply the go/no-go gate from Task 2 Step 3. If the gate passes, wiring a confirmed `GOALS_DISPERSION` constant into `LineupModel.predict()`/`_ou_prob_over25()` and the live engine is a separate, later plan (not part of this one — this plan is investigation only, matching the design spec). If the gate does not pass at any dispersion value, that is also a valid, useful result: it rules out this specific hypothesis with rigor, the same way `RESULTS.md`'s prior phases ruled out other approaches.
