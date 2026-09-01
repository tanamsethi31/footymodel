# Fixture Window Fix & Weekend Backfill Design

## Overview

The live-prediction engine permanently drops any fixture once its kickoff time has passed, with no retry — even though the confirmed-lineup data it needs never expires. Combined with GitHub Actions' scheduled-trigger reliability degrading sharply since Aug 27 (confirmed via `gh run list`: runs that fired every 30-60min on Aug 25-26 dropped to 6-19 hour gaps from Aug 27 onward, despite every individual run itself completing in under a minute), this caused 5 real Premier League matches from the Aug 30-31 weekend to never get a prediction logged at all (Aston Villa v Arsenal, Chelsea v Brighton, Leeds v Brentford, Sunderland v Fulham, Manchester United v Ipswich). Confirmed directly against the live API that lineup data for these fixtures is still fully retrievable now.

This covers two things: (1) a permanent fix so a future cron gap doesn't lose fixtures the same way, and (2) recovering the 5 fixtures already lost this way.

## Root Cause

The actual production entry point is `footymodel/live/run_all.py`'s `run_once()` (invoked by `.github/workflows/live_poll.yml` via `python -m footymodel.live.run_all`) — not `footymodel/live/engine.py`'s own `LiveWatcher.run_once()`, which is unused in production (only reachable via manual `python -m footymodel.live.engine` or `scripts/live_dryrun.py`, but shares the identical bug).

Both places filter candidate fixtures with:
```python
mins_to_ko = (kickoff - now).total_seconds() / 60
if not (0 <= mins_to_ko <= hours_ahead * 60):
    continue
```
Once `mins_to_ko` goes negative (kickoff has passed), the fixture is skipped forever — there's no path back to it on a later poll, regardless of whether that poll happens 5 minutes or 5 days later. Confirmed starting lineups publish only 20-40 minutes pre-kickoff, so any poll gap that straddles that narrow window loses the fixture permanently, even though lineup data itself is static and fetchable indefinitely afterward.

`run_all.py`'s fixture list (`all_fixtures`) is built from `{today, today+1, today+2}` date buckets — this doesn't block fixing same-day cron gaps (all 5 real misses happened on a day whose bucket *was* fetched; only the `mins_to_ko >= 0` cutoff excluded them afterward), but it does mean a fixture's date bucket eventually rolls out of that 3-day forward window entirely. A poll running today can no longer see Aug 30/31 fixtures at all, regardless of the `mins_to_ko` fix — which is why the backfill needs its own explicit date-fetch, not just a wider window on the regular poll.

## Fix 1: Widen the window (ongoing resilience)

`engine.py` gets a new constant alongside the existing `DEFAULT_HOURS_AHEAD = 2`:
```python
DEFAULT_HOURS_BEHIND = 24
```
24 hours comfortably covers same-day cron gaps (the actual failure mode observed) plus a safety margin for late-UTC kickoffs near a day boundary, at a bounded cost — no extra date-fetch calls, just one extra lineup-check per not-yet-`seen` fixture per poll until it's either confirmed-and-processed or ages out of the window.

Both `run_all.py`'s `run_once()` and `engine.py`'s `LiveWatcher.run_once()` change their window check to:
```python
if not (-hours_behind * 60 <= mins_to_ko <= hours_ahead * 60):
    continue
```
with `hours_behind: int = DEFAULT_HOURS_BEHIND` added as a parameter to both functions, mirroring the existing `hours_ahead` parameter.

## Fix 2: Extract a shared per-fixture helper

`run_all.py`'s loop body (fetch lineups → skip if not confirmed → fetch odds → run the goals engine → run the props engine if applicable → mark seen) is pulled into one function, `process_one_fixture(fx, client, goals, props, div)`, returning `None` if lineups aren't confirmed yet (caller should NOT mark the fixture `seen` — it may get confirmed on a later poll) or `(goal_row_or_None, prop_rows)` if lineups were confirmed and processing was attempted (caller SHOULD mark it `seen` regardless of whether a valid prediction came out, matching today's exact behavior — a confirmed-but-unmatched fixture is not worth retrying, since the lineup data won't change). Both `run_all.py`'s regular poll loop and the new backfill script (Fix 3) call this same function, so the fetch/process/error-handling logic exists in exactly one place.

## Fix 3: Reusable backfill script

New `scripts/backfill_missed_fixtures.py`. Usage:
```
python scripts/backfill_missed_fixtures.py 2026-08-30 2026-08-31
```
Takes one or more explicit `YYYY-MM-DD` dates as arguments. For each date, fetches that date's fixtures directly via the same `ApiFootballClient.fixtures_by_date()` used elsewhere (bypassing the rolling 3-day forward window entirely, since a backfill's whole purpose is reaching dates that have already rolled out of it), filters to tracked leagues, skips anything already in the shared `seen` set (loaded via `engine.py`'s existing `_load_seen()`), and calls `process_one_fixture()` for everything else — appending any new rows to the exact same `data/processed/live_recommendations.csv` / `data/processed/live_player_props.csv` the regular poll writes to, and saving the updated `seen` set back via `_save_seen()`.

Because it shares the same `seen` set and output files as the regular poll, running this script can never double-log a fixture the regular poll already caught, and anything it does log here will never be reprocessed by a later regular poll either — no special-casing needed on either side.

## Recovering the 5 missed matches

After both fixes are implemented and tested:
1. Run `python scripts/backfill_missed_fixtures.py 2026-08-30 2026-08-31` locally, confirm it logs new rows for the 5 real matches (or reports honestly if some can't be matched — e.g. if starters-matched falls below the 8/11 threshold for any of them, that fixture is correctly skipped just like it would be in the regular poll, not force-included).
2. Commit and push the updated CSVs (and `match_detail.jsonl`, `live_seen_fixtures.json`) to `origin/main`.
3. Manually trigger `grade_results.yml` (`gh workflow run`) so the Track Record tab picks up these matches too — all 5 have already finished, so real final scores are available immediately, closing the "sequence of past matches" gap directly.

## Error Handling

- `process_one_fixture()` already wraps each of its external calls (lineups fetch, odds fetch, the goals engine, the props engine) in the same try/except-and-print pattern `run_all.py` uses today — one fixture's failure doesn't abort the whole poll or backfill run.
- The backfill script fetching an invalid/future date, or a date with no fixtures at all, prints the same `"! fixtures fetch failed for {date}: {e}"` style message the regular poll already uses for a failed date-fetch, and simply logs nothing for that date rather than crashing.

## Testing

This repo's live-engine code has existing plain-assert test scripts (`scripts/run_all_dryrun.py`, `scripts/run_all_upcoming_test.py`) wired into CI, following the same pattern used throughout this project (no pytest, no fixtures/mocks framework — synthetic in-memory data + `assert`). This work adds to that same pattern:
- Update `scripts/run_all_dryrun.py`'s existing mock-fixture test data to include a case where kickoff has already passed (e.g. -60 minutes) with confirmed lineups, and assert it still produces a logged prediction — this is the core behavior this fix adds, and this file already exercises `run_all.run_once()`'s full loop end-to-end against mocked lineups/odds, so it's the natural place to add the regression coverage.
- A new small test script, `scripts/backfill_missed_fixtures_test.py`, exercising `process_one_fixture()` directly (already covered indirectly by `run_all_dryrun.py`, but a focused test isolates its two return shapes — `None` for unconfirmed, a tuple for confirmed-and-processed) with synthetic in-memory fixture/lineup data, no real network calls.
- The actual backfill run against the 5 real weekend matches is manual verification, not an automated test (it's a one-time recovery action against live data, not a repeatable CI case) — success is judged by the resulting `live_recommendations.csv` rows and the live dashboard showing them afterward.
