# Expandable Match Detail — Design

## Goal

Clicking a match card in the dashboard's Goals O/U tab expands it in place to show how the model arrived at its prediction: a team-model vs. lineup-model vs. blended breakdown, a plain-English confidence read, and the actual starting XI for both teams — instead of just the final blended numbers and a starter count, which is all that's shown today.

## Background

The dashboard's `getGoalsPicks()` (`dashboard/lib/data.ts:186-221`) surfaces 16 fields per match, all already used in the current card: `loggedAt, fixtureId, league, kickoff, home, away, nHomeMatched, nAwayMatched, modelPOver25, expTotalGoals, oddsOver25, oddsUnder25, source, fairPOver25, evOver25, evUnder25`.

Each live engine (`footymodel/live/engine.py`, `rapidapi_engine.py`, `sofascore_engine.py`) computes more than this at prediction time inside `process_fixture()`, then discards most of it before writing to `live_recommendations.csv`:

- **Starting XI names** — `engine.py:143-144` builds `home_names`/`away_names` (and matched `home_ids`/`away_ids`) right before calling the model; only `len(home_ids)`/`len(away_ids)` survive into the logged row.
- **Team-model vs. lineup-model breakdown** — `LineupModel.predict()` (`footymodel/players.py:234-260`) returns `exp_team, exp_full, exp_blend, p_over25_team, p_over25_full, p_over25_blend`; only the `_blend` values are logged today.

`live_recommendations.csv`'s ragged trailing-column format has already caused two bugs this session (R050, R072) from growing optional fields over time — see `dashboard/lib/data.ts`'s `getGoalsPicks()` and `footymodel/live/grade_results.py`'s `parse_prediction_row()`. This design avoids adding a third variant of that problem.

## Backend: `match_detail.jsonl`

A new file, `data/processed/match_detail.jsonl`, one JSON object per line, one line per graded prediction, keyed by `fixture_id`:

```json
{"fixture_id": 1557370, "home_starters": ["Ederson", "Walker", "..."], "away_starters": ["Henderson", "..."], "exp_team": 2.9, "exp_full": 3.2, "p_over25_team": 0.58, "p_over25_full": 0.63}
```

Same schema regardless of which engine writes it. Unlike the CSV, JSONL has no header/positional-column concept — each line is self-contained, so there is no ragged-column failure mode here even though different engines may populate it at different times.

Each of the three engines' `process_fixture()` methods already has everything needed in scope (starter name lists, the full `pred` dict) at the point where they currently build the CSV `row` dict. Each one builds a second `detail` dict alongside `row` and returns both; `run_once()` collects both lists and, after writing `live_recommendations.csv` exactly as it does today, separately appends the new detail rows to `match_detail.jsonl` inside their own try/except. A failure writing the detail file must never prevent the actual prediction from being logged — the CSV write happens first and is unaffected by anything that follows.

This is purely additive: `live_recommendations.csv` and its existing parsing (`data.ts`, `grade_results.py`) are untouched. Only predictions logged after this ships get a `match_detail.jsonl` entry — older rows simply have no matching line.

## Frontend: `MatchCard` component

Today, each Goals O/U row is inline JSX inside a `GoalsPanel` function in `dashboard/app/page.tsx` (lines 124-187) — a Server Component, no interactivity. This becomes:

- **`dashboard/components/MatchCard.tsx`** (new, `"use client"`) — one match's card, holding a single `useState` for expanded/collapsed. Receives `match: GoalsPick` and `detail: MatchDetail | null` as props.
- `GoalsPanel` (still in `page.tsx`, still a Server Component) maps over matches and renders `<MatchCard key={g.fixtureId} match={g} detail={detailByFixtureId[g.fixtureId]} />` instead of the current inline `<div>`.
- `getGoalsPicks()` in `data.ts` additionally fetches `match_detail.jsonl` via the same GitHub Contents API mechanism already used for the CSVs, parses it line-by-line as JSON, and exposes a `fixtureId -> MatchDetail` lookup that `page.tsx` passes down. A match with no entry gets `detail: null` — this is the expected, common case for any prediction logged before this ships and must never throw.

**Interaction:** the whole card is clickable (`onClick`, plus `role="button"`, `tabIndex={0}`, and Enter/Space keyboard support), with a small rotating chevron SVG (matching `Logo.tsx`'s inline-SVG style) indicating expanded/collapsed state. The existing stat grid and starters-matched line render exactly as they do today, unchanged, whether expanded or not.

**Expanded content**, when `detail` is present:
- **Model breakdown** — three rows (team-based, lineup-based, blended), each showing xG total and P(O2.5), making the existing "Model P(O2.5)" value visible as the blend of the other two.
- **Confidence line** — one sentence comparing `p_over25_team` and `p_over25_full`: small gap ⇒ "Team and lineup models agree closely"; larger gap ⇒ "Team and lineup models diverge" (threshold: 0.05).
- **Starting XI** — two columns (home/away), starter names as plain text.

**Expanded content**, when `detail` is `null` (older prediction, or the detail file failed to write for that fixture): the section still opens, but shows only a single muted line — "Detailed breakdown not available for this prediction." No broken layout, no missing-field errors.

## Error handling

- Detail-file write failure in any engine: isolated to that engine's own try/except, after the CSV write — never blocks or corrupts the actual prediction log.
- Missing `match_detail.jsonl` entirely (e.g. first deploy before any engine has run since shipping this): dashboard treats it as "no detail for any match" — same code path as a single missing entry, not a special case.
- Empty starter arrays (lineup fetched but too few matched): render as an empty/omitted list, not an error.

## Testing

- A data-free Python unit test (matching the style of `scripts/grade_results_columns_test.py`) covering the new detail-row shape and the fixture_id join, wired into `.github/workflows/ci.yml`.
- No new TypeScript test framework — the dashboard side has never had one this session; verification stays `tsc --noEmit` + `next build` + manual browser check via the Browser pane, consistent with every other frontend change made this session.

## Out of scope

- Head-to-head history (not available from any current data source — would need a new API integration).
- Per-player attack/defence rating breakdown (exists as intermediate state inside the fitted `LineupModel` but summed away before `predict()` returns; showing it would need a separate, larger change).
- Cross-bookmaker "best odds available" comparison (a different, unrelated feature — the Glossary already explains what a given decimal-odds value like "@1.01" means).
- Backfilling `match_detail.jsonl` for historically-logged predictions.
