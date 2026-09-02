# Live Closing-Odds Capture + CLV

## Overview

Testing whether the live Phase B window (capturing lineup news before the market re-prices) has real edge requires Closing Line Value (CLV) — this project's own established gold-standard, low-noise edge signal (`RESULTS.md` Phases 3b/C: `clv = open_odds/close_odds - 1`, positive mean CLV / >50% beat-close rate is the bar). The live pipeline cannot compute this today: it captures odds exactly once per fixture, at lineup-confirmation time (`process_one_fixture()` marks a fixture "seen" once processed, specifically so it's never revisited), so there is no later "closing" snapshot to compare against.

This adds a same-source closing-odds fetch to `grade_results.py`'s existing post-match grading pass — the pass that already runs well after full-time and already resolves each fixture's final score — and computes `bet_clv` on every graded pick. No changes to the live poll cadence, no new "seen" tracker, no changes to `run_all.py`/`engine.py`/`rapidapi_engine.py`/`sofascore_engine.py`'s prediction logic. This produces no immediate verdict — CLV only becomes meaningful once real samples accumulate over weeks, same as every prior CLV result in this project's history — but it's the prerequisite the accumulation needs, and grading starts capturing it from the next run onward.

**A correction made while writing this spec:** the original approach description said this "reuses existing prefix-based client routing" — that was wrong. Re-reading `grade_results.py`'s `grade_row()`, BOTH of its existing lookup paths (`fixture_by_id()` and the date+fuzzy-name fallback) only ever use `ApiFootballClient`, regardless of which engine produced the row. There is no existing per-source client dispatch to reuse. This spec adds it as new plumbing.

## Components

### Per-source client dispatch (new)

`grade_results.py`'s `main()` currently constructs one `ApiFootballClient()` and passes it to every `grade_row()` call. It now inspects `to_grade["fixture_id"]` up front and constructs additional clients only if rows of that source are actually present in this run's batch:

- Plain integer `fixture_id` → `ApiFootballClient` (already constructed today).
- `rapid_<event_id>` → `RapidApiClient`, reusing `rapidapi_engine.py`'s existing `_load_budget()`/`_save_budget()`/`BUDGET_CAP` mechanism and `rapidapi_budget.json` — the closing-odds fetch shares the SAME monthly budget the live engine draws from (currently 1/100 used), so it must check and deduct through the same accounting, not bypass it. If the budget is exhausted, closing-odds fetches for `rapid_`-prefixed rows are skipped (logged, not fatal) exactly like the existing engine's own budget-exhausted skip.
- `sofa_<event_id>` → `SofaScoreClient`, constructed once (it owns a real Playwright browser context) and reused across every `sofa_`-prefixed row in the batch, closed at the end of the run.

A `clients: dict[str, object]` (keys: `"apifootball"`, `"rapidapi"`, `"sofascore"`, only the ones actually needed) is threaded into `grade_row(row, cache, clients)` in place of the current single `client` parameter.

### `_fetch_closing_odds(fixture_id: str, clients: dict) -> tuple[float | None, float | None]`

New function in `grade_results.py`. Given a row's `fixture_id`, dispatches to the matching client's own `.odds()` method and the matching engine's own already-tested odds-parsing helper — same parsing logic used at prediction time, just called again later, since the raw response shape from a given source doesn't change between confirmation-time and grading-time:

- `rapid_...` → `RapidApiClient.odds(event_id, countrycode=ODDS_COUNTRYCODE)` (same `countrycode` constant `rapidapi_engine.py` already uses) → `rapidapi_engine._find_25_line(resp)`.
- `sofa_...` → `SofaScoreClient.odds(event_id)` → `sofascore_engine._find_25_line(resp)`.
- plain id → `ApiFootballClient.odds(int(fixture_id))` → `engine._best_over_under_odds(resp)`.

Returns `(None, None)` on any exception (budget exhausted, network error, empty response, or a source-specific client simply not being available this run) — a missing closing snapshot must never block grading the outcome itself, exactly the same non-fatal-degradation principle `grade_row()` already applies to its own odds-fetch-failed cases today.

### `bet_clv` computation

Inside `grade_row()`, after the existing `bet_side`/`bet_odds`/`bet_won`/`realized_return` block: call `_fetch_closing_odds()`, pick the closing price for the SAME side that was actually bet (`closing_over25` if `bet_side == "over"`, else `closing_under25`), and compute `bet_clv = round(bet_odds / closing_bet_odds - 1, 4)` — the identical formula `backtest.py`'s `clv = open_odds/close_odds - 1` already established, with the live pipeline's confirmation-time odds playing the role of "open" and this new snapshot playing the role of "close". `bet_clv` stays `None` whenever `bet_side` is `None` (no bet was made) or the closing fetch failed/returned nothing for that side.

### New `graded_results.csv` columns

`closing_odds_over25`, `closing_odds_under25` (the raw snapshot, for anyone auditing later), and `bet_clv`. All three are additive — every existing column and existing row shape is unchanged, so nothing downstream that already reads `graded_results.csv` (the dashboard, `live_summary.py`) breaks; they simply won't have these columns populated for rows graded before this ships.

## Data Flow

Unchanged: `live_recommendations.csv` (written by whichever engine confirmed lineups first) → `grade_results.py` reads ungraded rows past `GRADE_DELAY_HOURS` → resolves final score (existing, unchanged) → NEW: resolves closing odds via the matching source's client → computes `bet_clv` → appends to `graded_results.csv`.

## Error Handling

- Any closing-odds fetch failure (budget exhausted, network/API error, empty response) is caught, printed as a non-fatal warning (matching the existing `! odds fetch failed` convention already used in `engine.py`/`rapidapi_engine.py`/`sofascore_engine.py`), and results in `bet_clv = None` for that row — grading of the actual match outcome (`model_correct`, `bet_won`, `realized_return`) is completely unaffected and unchanged.
- `SofaScoreClient`'s Playwright browser context is only started if at least one `sofa_`-prefixed row needs grading this run (avoids an unnecessary browser launch on every grading run when there's nothing for it to do), and is always closed in a `finally` block even if some fixtures in the batch fail — matching the existing "always `.remove()`/close in a `finally`" discipline this project already established for browser-context resource leaks (Phase E).
- `RapidApiClient`'s budget check happens before every closing-odds attempt, sharing state with the live engine's own budget file — a graded run must never push `calls_used` over `BUDGET_CAP` on its own or in combination with the live engine's usage earlier that month.

## Testing

Following this project's established convention for `live/` production code (e.g. `grade_results_by_id_test.py`, `run_all_dryrun.py`): a new `scripts/grade_results_clv_test.py` with mocked clients (no real network/API calls, no real Playwright browser, no real budget file), covering:
- A plain-API-Football-sourced row: closing odds fetched via a mocked `ApiFootballClient.odds()`, `bet_clv` computed correctly against a known `bet_odds`.
- A `rapid_`-prefixed row: mocked `RapidApiClient.odds()`, and a mocked/temp budget file confirming the fetch correctly checks and deducts the shared budget (and correctly SKIPS the fetch, returning `(None, None)`, when the budget is already exhausted).
- A `sofa_`-prefixed row: mocked `SofaScoreClient.odds()`.
- A closing-odds fetch that raises/fails: confirms `bet_clv` is `None` and the rest of that row's grading (outcome, `model_correct`, etc.) still completes normally.
- A row with `bet_side is None` (no bet was made): confirms `bet_clv` stays `None` without even attempting a closing-odds fetch (nothing to compute CLV against).

Wired into `.github/workflows/ci.yml` alongside the existing `grade_results_by_id_test.py`/`grade_results_columns_test.py`/`grade_results_datetime_test.py` steps.

## Out of scope (future work, not this spec)

Reading back the accumulated `bet_clv` values once enough live samples exist — pooled CLV, beat-close rate, significance test, mirroring `backtest.py`'s `summarize_bets()` — is a separate, later analysis task. There is nothing meaningful to report until real matches accumulate over the coming weeks; this spec only makes that eventual analysis possible.
