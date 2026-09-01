# Goals-Level Negative-Binomial Dispersion Test

## Overview

`LineupModel.predict()` (`footymodel/players.py`) converts its expected-total-goals estimate into an Over/Under 2.5 probability via a plain Poisson (`_ou_prob_over25`). The project's own shots submodel already discovered that a point-estimate Poisson is "too sharp-tailed" for count data — real shot counts are overdispersed, and a Negative Binomial with a tuned dispersion parameter fixed persistent overconfidence at the 50-90% probability range (`SHOTS_DISPERSION = 3.0`, confirmed via `scripts/shots_calibration_test.py`). Nobody has ever run the same test on the goals-level Over/Under prediction, even though total goals is exactly the kind of count variable likely to show the same overdispersion. This adds a new investigative script, `scripts/goals_dispersion_test.py`, that runs the identical methodology against the goals model, to find out whether the same fix applies here.

This is purely an investigation to produce evidence. It does not modify `LineupModel`, `players.py`, or any production/live code — if the test finds a dispersion value that passes the go/no-go gate below, wiring it into the live model is a separate follow-up.

## Components

### `evaluate(players, leagues) -> pd.DataFrame`

Walk-forward evaluation, one row per match: `{league, exp_team, exp_full, over_won}`. Built on `players.py`'s existing `accuracy_test()` (already does the walk-forward fit + prediction, no lookahead) — this function just loops it across leagues and concatenates, exactly like `shots_calibration_test.py`'s `evaluate()` loops per-league then per-date.

- `LEAGUES = ["E0", "SP1", "D1", "I1", "F1"]` — the same big-5 set the full-lineup fix was validated on (`RESULTS.md`'s cross-league confirmation table), not just E0.
- `TEST_START = "2022-07-01"`, `MIN_TRAIN_ROWS` matching `accuracy_test()`'s existing default (`5000`) — no new tuning here, reuse what's already validated.
- Cached to `data/processed/goals_eval_cache.parquet` (mirrors `shots_eval_cache.parquet`) so re-running the sweep with a different dispersion value doesn't re-run the expensive walk-forward fit.

### `calibrate_league(raw, target_mean) -> np.ndarray`

Local copy of `lineup_test.py`'s existing scale-calibration helper (binary-searches a multiplicative scale on the raw expected total so the Poisson-implied mean P(over) matches the league's actual over-rate). Duplicated here rather than extracted into a shared module — `lineup_test.py` and `shots_calibration_test.py` already each keep their own small conversion helpers rather than sharing one across two call sites, and a third near-identical 12-line copy keeps that same pattern rather than introducing a new shared abstraction for what is still just two real call sites after this change.

Run once per league on `exp_blend` (see below) before any dispersion sweep — this isolates the tail-shape question (dispersion) from the mean-bias question, which is separate and already settled.

### `exp_blend` construction

`exp_blend = BEST_BLEND_W * exp_team + (1 - BEST_BLEND_W) * exp_full`, using `players.py`'s existing `BEST_BLEND_W = 0.25` constant — the already-confirmed, already-live production blend. Computed downstream in the new script from the two cached columns; no change to `accuracy_test()`'s return shape.

### `simulate(evals, dispersion) -> None`

Cheap step, run once per candidate dispersion value without re-fitting. For each league (and pooled):

1. Scale-calibrate `exp_blend` via `calibrate_league()`, per league (each league gets its own fitted scale, matching `lineup_test.py`'s existing per-league loop).
2. Convert to a probability: `poisson.cdf` if `dispersion is None`, else `nbinom.cdf` with `(n, p) = (dispersion, dispersion / (dispersion + lam))` — identical formula to `players.py`'s existing `prob_over()`.
3. Print Brier score and `footymodel.backtest.calibration_table(...)` (existing shared function, already used by `shots_calibration_test.py`) for that league individually, then again pooled — "pooled" means concatenating every league's scale-calibrated predictions and outcomes into one array before computing Brier/calibration/t-stat, exactly how `lineup_test.py` produces its own pooled row.

Dispersion sweep: `[None, 1, 2, 3, 4, 5, 6, 8, 10, 15]` — same range convention that found `3` as the knee for shots.

### Significance check

For the pooled-Brier-best dispersion value found in the sweep, compute the paired t-stat of squared-error between it and the `None` (Poisson) baseline — identical method to `lineup_test.py`'s own full-vs-team-model significance test (`t = mean(diff) / (std(diff) / sqrt(n))`).

## Data Flow

`load_players()` (existing) → `accuracy_test()` per league (existing, unchanged) → `evaluate()` concatenates + caches to parquet → `simulate()` reads the cache, applies scale-calibration + a chosen dispersion, prints Brier/calibration/t-stat. Re-running with a different dispersion value only re-runs `simulate()` (cache hit), matching the two-stage cost model `shots_calibration_test.py` already established.

## Error Handling

No new failure modes beyond what `accuracy_test()` and `calibrate_league()` already handle (both existing, unchanged). This is a read-only, offline analysis script — no live data, no network calls, no writes outside its own cache file.

## Go/No-Go Gate

A dispersion value is worth adopting into production only if, at the pooled level:

1. It improves pooled Brier vs the Poisson baseline.
2. The improvement is statistically significant: paired t-stat > 2 (the same threshold used throughout `RESULTS.md` and `lineup_test.py`).
3. It improves or is neutral on **every individual league** in the sweep — not just a pooled average driven by one league. This is the exact bar that caught the half-lineup model's false positive (looked good on PL alone, didn't replicate on Ligue 1).

If the gate passes, wiring a confirmed `GOALS_DISPERSION` constant into `LineupModel.predict()`/`_ou_prob_over25()` and the live engine is a separate, later plan — explicitly out of scope for this script.

## Testing

This script IS the test — its whole purpose is to produce the Brier/calibration/significance numbers that answer the hypothesis. There's no separate unit test to write beyond the sanity of reusing already-tested functions (`accuracy_test()`, `calibrate_league()`-equivalent logic, `calibration_table()`, `prob_over()`'s NB formula) — consistent with how `shots_calibration_test.py` itself has no separate test file, since it's a one-shot analysis script, not a production code path.
