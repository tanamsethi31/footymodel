# Richer Push Notification Content

## Overview

`scripts/notify_dashboard.py` (called from `live_poll.yml` right before it commits new prediction rows) currently sends a push notification listing only team names — e.g. title `"4 new footymodel prediction(s)"`, body `"Goals: Chelsea v Brighton, Leeds v Brentford +2 more"`. This adds the model's own headline numbers (P(O2.5), expected total goals) to the notification, so it gives real insight into a prediction on its own, not just a bare fixture list.

## Components

### Featured-fixture selection (multi-fixture case)

When more than one new goals prediction lands in a single poll, one fixture is picked to display in full detail; the rest are tallied. The featured fixture is whichever has the largest distance from a coin-flip call: `max(goals, key=lambda r: abs(float(r["model_p_over25"]) - 0.5))`. This is a reliable, always-available signal — every goals row already has `model_p_over25` populated, whereas EV/odds are only present when a market price was fetched at logging time, so distance-from-50% is used instead of EV to avoid a fallback branch for missing data.

### Body format

Only `live_recommendations.csv`'s own columns are used — `model_p_over25` (as a rounded percentage) and `exp_total_goals` (to 2 decimal places) — no new data source (`match_detail.jsonl` is NOT read here; its richer confidence/starting-XI content stays exclusive to the dashboard's expandable card, keeping this change to one data source).

- **One new goals prediction:** the "Goals: ..." line becomes `"{home} v {away}: {pct}% O2.5, xG {exp:.2f}"` — e.g. `"Chelsea v Brighton: 44% O2.5, xG 2.43"`.
- **Multiple new goals predictions:** same format for the featured fixture, with a tally suffix — `"{home} v {away}: {pct}% O2.5, xG {exp:.2f} (+{N-1} more)"` — e.g. `"Chelsea v Brighton: 44% O2.5, xG 2.43 (+3 more)"`.
- **No new goals predictions** (only player-props landed): unchanged from today — this change only touches the goals-line construction.

The notification's `title` (a plain count, e.g. `"4 new footymodel prediction(s)"`) and the player-props summary line (`"Props: N fixture(s), M player line(s)"`) are both unchanged. The two are still joined with `" | "` exactly as today.

This logic is pulled into its own small function, `build_goals_line(goals: list[dict]) -> str`, called from `main()` in place of the current inline `if goals: ...` block — the only reason for the extraction is to make the featured-fixture selection and formatting directly unit-testable with synthetic row dicts (see Testing below), without needing to fake a git diff or an HTTP call just to exercise this one piece of string-building.

## Data Flow

No change to how rows reach `notify_dashboard.py` — `_new_rows()` already reads newly-staged CSV rows from the git diff exactly as today, and both `model_p_over25`/`exp_total_goals` are already present in every row it parses (`live_recommendations.csv`'s header always includes them, per `grade_results.py`'s own `_BASE_COLUMNS` list, which documents these as always-written fields). Only the string-building step inside `main()` changes.

## Error Handling

- `float(r["model_p_over25"])` / `float(r["exp_total_goals"])`: both fields are always written by every engine that logs a goals row (confirmed: they're part of the row dict in every `process_fixture()`/`process_one_fixture()` return path across `engine.py`, `rapidapi_engine.py`, `sofascore_engine.py`), so no missing-value fallback is needed for the featured-fixture case itself.
- The existing top-level behavior is unchanged: if `NOTIFY_URL`/`NOTIFY_SECRET` aren't set, or nothing new was staged, the script no-ops exactly as today; a failed POST is still caught and logged as non-fatal, never blocking the actual git commit.

## Testing

This repo's other scripts in this area (e.g. `scripts/grade_results_columns_test.py`) already use plain `assert`-based synthetic-data tests, wired into CI. Following the same pattern: a new `scripts/notify_dashboard_test.py` exercises the body-building logic directly with synthetic row dicts (not the actual git-diff/HTTP-POST parts, which aren't practical to unit test without real git state or network mocking) — covering the one-fixture case, the multi-fixture featured-selection case (confirming the correct fixture is chosen when probabilities vary), and the props-only case (confirming the goals line is absent and the rest is unchanged).
