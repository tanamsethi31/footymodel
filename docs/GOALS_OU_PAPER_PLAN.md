# Plan — Goals O/U 2.5 back on shared €100 paper bankroll

## Objective

Re-enable the **lineup-aware Over/Under 2.5** model on the **same SofaScore +
€100 ledger** as player shots/SOT. No paid live APIs. One bankroll, one bet
CSV, unified settlement.

## Phase 1 — Mathematics audit (offline)

- Verify `LineupModel` blend (`BEST_BLEND_W=0.25`), Poisson O/U mapping, and
  `remove_margin` + EV (`p×odds−1`) match `sofascore_engine.py` / `grade_results.py`.
- Re-state historical verdict from `RESULTS.md` (closing-line backtest: no edge;
  live lineup window is the open hypothesis).
- Script: `scripts/goals_ou_math_audit.py` (CI-wired).

## Phase 2 — Unified paper ledger

- Extend ledger with `bet_kind`: `props` | `goals_ou`.
- Goals bets: at most **one** O/U 2.5 pick per fixture when both SofaScore odds
  exist and best-side **EV ≥ 2%**; stake via **¼ Kelly**, max **2%** bankroll.
- Shared per-fixture exposure cap (8%) across props + goals.
- Module: `footymodel/live/paper_bankroll.py` (`paper_props_bankroll.py` re-exports).

## Phase 3 — Live poll (home network)

- `sofascore_matchday.py`: one Playwright session → goals engine then props engine.
- Align goals poll window with props (**180 min lookback**, 2h ahead).
- `matchday_laptop.sh` runs matchday module + settlement.

## Phase 4 — Settlement (cloud-friendly)

- Props: `graded_props_players.csv` (unchanged).
- Goals: `graded_results.csv` rows matched by `fixture_id`.
- `grade_results.py`: score lookup from **`matches.parquet`** (free) when no API
  keys; SofaScore event API as secondary for `sofa_*` ids when run locally.

## Phase 5 — Dashboard & docs

- Dashboard tab **Goals O/U** + paper bet lines on Track record.
- README + `SHOTS_SOT_OPERATING.md` → rename scope to full paper product.

## Success criteria

- `goals_ou_math_audit.py` passes in CI.
- `paper_props_bankroll_test.py` covers goals + props settlement.
- Match-day script logs `live_recommendations.csv` and places goals paper bets.

## Status (implemented)

Phases 1–5 are in `cursor/goals-ou-paper-bankroll-61ac`: unified ledger,
`sofascore_matchday`, `grade_results` parquet lookup, dashboard **Goals O/U** tab,
and updated operating docs.
