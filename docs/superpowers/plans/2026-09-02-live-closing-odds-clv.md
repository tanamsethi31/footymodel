# Live Closing-Odds Capture + CLV Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `grade_results.py` fetch a same-source closing-odds snapshot for every graded prediction and compute `bet_clv`, so real Closing Line Value evidence starts accumulating from the next grading run onward — the prerequisite for ever answering whether the live Phase B window has real edge.

**Architecture:** `grade_results.py`'s `main()` builds one client per data source actually present in the current grading batch (`ApiFootballClient` always; `RapidApiClient`/`SofaScoreClient` only if `rapid_`/`sofa_`-prefixed rows need grading this run), threaded into `grade_row()` as a `clients` dict in place of today's single `client` param. A new `_fetch_closing_odds()` dispatches on the `fixture_id` prefix to the matching client and that source's own already-tested odds-parsing helper (`engine._best_over_under_odds`, `rapidapi_engine._find_25_line`, `sofascore_engine._find_25_line`), sharing the RapidAPI engine's own `rapidapi_budget.json` accounting so a grading run can never push the shared monthly quota over its cap.

**Tech Stack:** Python 3.11 (repo venv: `.venv/bin/python`), `unittest.mock.MagicMock` for the client mocks (matching `grade_results_by_id_test.py`'s existing convention — no pytest anywhere in this repo).

See spec: `docs/superpowers/specs/2026-09-02-live-closing-odds-clv-design.md`

---

### Task 1: Same-source closing-odds fetch + `bet_clv`

**Files:**
- Modify: `footymodel/live/grade_results.py`
- Create: `scripts/grade_results_clv_test.py`
- Modify (one-time data migration): `data/processed/graded_results.csv`

- [ ] **Step 1: Write the test first**

Create `scripts/grade_results_clv_test.py`:

```python
"""Unit-check for grade_results.py's new same-source closing-odds fetch and
bet_clv computation: confirms each fixture_id prefix (plain API-Football,
rapid_, sofa_) dispatches to its OWN matching client rather than mixing
sources, that the shared RapidAPI monthly budget is actually checked and
deducted (and correctly skipped once exhausted), and that a failed/absent
closing-odds fetch degrades to bet_clv=None without blocking the outcome
grading that already worked before this change. Pure/data-free (mocked
clients, no real network/Playwright/budget file) - safe to run in CI."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live import grade_results, rapidapi_engine
from footymodel.live.client import ApiFootballError
from footymodel.live.rapidapi_client import RapidApiError
from footymodel.live.sofascore_client import SofaScoreError

finished_fixture = {
    "fixture": {"id": 1557379, "status": {"short": "FT"}},
    "league": {"id": 39},
    "teams": {"home": {"name": "Chelsea"}, "away": {"name": "Brighton"}},
    "goals": {"home": 1, "away": 2},
}


def _row(fixture_id: str) -> pd.Series:
    return pd.Series({
        "fixture_id": fixture_id, "home": "Chelsea", "away": "Brighton",
        "kickoff": "2026-08-30T13:00:00+00:00", "model_p_over25": 0.439,
        "ev_over25": 0.10, "ev_under25": float("nan"),
        "odds_over25": 2.00, "odds_under25": None,
    })


# --- plain API-Football fixture_id: closing odds via ApiFootballClient.odds() ---
mock_apifootball = MagicMock()
mock_apifootball.fixture_by_id.return_value = finished_fixture
mock_apifootball.odds.return_value = [{"bookmakers": [{"bets": [
    {"name": "Goals Over/Under", "values": [
        {"value": "Over 2.5", "odd": "1.80"}, {"value": "Under 2.5", "odd": "2.05"}]}]}]}]

clients = {"apifootball": mock_apifootball}
result = grade_results.grade_row(_row("1557379"), {}, clients)
assert mock_apifootball.odds.call_count == 1
assert result is not None
assert result["bet_side"] == "over"  # ev_over25=0.10 > 0
assert result["closing_odds_over25"] == 1.80
assert result["bet_clv"] == round(2.00 / 1.80 - 1, 4), result["bet_clv"]
print("apifootball-sourced closing odds + CLV: OK")

# --- rapid_-prefixed fixture_id: closing odds via RapidApiClient.odds(),
# shared monthly budget checked and deducted ---
mock_rapidapi = MagicMock()
mock_rapidapi.odds.return_value = {"odds": {"odds": {"oddsTabMarkets": [
    {"markets": [{"header": "Over/Under", "selections": [
        {"name": "Over 2.5", "oddsDecimal": 1.75}, {"name": "Under 2.5", "oddsDecimal": 2.10}]}]}]}}}
budget = {"month": "2026-09", "calls_used": 0}
clients_rapid = {"apifootball": mock_apifootball, "rapidapi": mock_rapidapi, "rapidapi_budget": budget}
result2 = grade_results.grade_row(_row("rapid_5868013"), {}, clients_rapid)
assert mock_rapidapi.odds.call_count == 1
assert budget["calls_used"] == 1, "closing-odds fetch must deduct the shared budget"
assert result2 is not None
assert result2["bet_clv"] == round(2.00 / 1.75 - 1, 4), result2["bet_clv"]
print("rapidapi-sourced closing odds + shared-budget deduction: OK")

# --- rapid_-prefixed, budget already exhausted: must skip the fetch, never
# call the client, bet_clv stays None, outcome grading still completes ---
exhausted_budget = {"month": "2026-09", "calls_used": rapidapi_engine.BUDGET_CAP}
mock_rapidapi2 = MagicMock()
clients_exhausted = {"apifootball": mock_apifootball, "rapidapi": mock_rapidapi2,
                     "rapidapi_budget": exhausted_budget}
result3 = grade_results.grade_row(_row("rapid_5868013"), {}, clients_exhausted)
assert mock_rapidapi2.odds.call_count == 0, "must not call the client once budget is exhausted"
assert result3 is not None
assert result3["bet_clv"] is None
assert result3["model_correct"] is not None  # outcome grading still worked
print("rapidapi budget-exhausted skip: OK")

# --- sofa_-prefixed fixture_id: closing odds via SofaScoreClient.odds() ---
mock_sofascore = MagicMock()
mock_sofascore.odds.return_value = [{"marketGroup": "Match goals", "choiceGroup": "2.5", "choices": [
    {"name": "Over", "fractionalValue": "4/5"}, {"name": "Under", "fractionalValue": "6/5"}]}]
clients_sofa = {"apifootball": mock_apifootball, "sofascore": mock_sofascore}
result4 = grade_results.grade_row(_row("sofa_12345"), {}, clients_sofa)
assert mock_sofascore.odds.call_count == 1
assert result4 is not None
assert result4["bet_clv"] is not None
print("sofascore-sourced closing odds + CLV: OK")

# --- closing-odds fetch raises: bet_clv stays None, outcome grading unaffected ---
mock_apifootball_fails = MagicMock()
mock_apifootball_fails.fixture_by_id.return_value = finished_fixture
mock_apifootball_fails.odds.side_effect = ApiFootballError("boom")
result5 = grade_results.grade_row(_row("1557379"), {}, {"apifootball": mock_apifootball_fails})
assert result5 is not None
assert result5["bet_clv"] is None
assert result5["model_correct"] is not None
print("closing-odds fetch failure degrades gracefully: OK")

# --- no bet was made (bet_side is None): bet_clv stays None, closing-odds
# fetch never even attempted ---
mock_apifootball_nobet = MagicMock()
mock_apifootball_nobet.fixture_by_id.return_value = finished_fixture
row_nobet = _row("1557379")
row_nobet["ev_over25"] = float("nan")
row_nobet["ev_under25"] = float("nan")
result6 = grade_results.grade_row(row_nobet, {}, {"apifootball": mock_apifootball_nobet})
assert mock_apifootball_nobet.odds.call_count == 0, "must not fetch closing odds when no bet was made"
assert result6["bet_side"] is None
assert result6["bet_clv"] is None
print("no-bet row skips closing-odds fetch entirely: OK")

print("ALL CHECKS PASSED — same-source closing-odds dispatch, shared RapidAPI "
      "budget accounting, and graceful degradation are all correct.")
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `.venv/bin/python scripts/grade_results_clv_test.py`
Expected: `AttributeError` or `TypeError` — `grade_row()` doesn't accept a `clients` dict yet, and `closing_odds_over25`/`bet_clv` don't exist on its return value.

- [ ] **Step 3: Implement the client dispatch and closing-odds fetch**

In `footymodel/live/grade_results.py`, find:

```python
from ..data import PROCESSED_DIR
from . import namematch
from .client import ApiFootballClient, ApiFootballError
```

Replace with:

```python
from ..data import PROCESSED_DIR
from . import namematch, rapidapi_engine, sofascore_engine
from .client import ApiFootballClient, ApiFootballError
from .engine import _best_over_under_odds
from .rapidapi_client import RapidApiClient, RapidApiError
from .sofascore_client import SofaScoreClient, SofaScoreError
```

Then, just above `def grade_row(...)`, add:

```python
def _spend_rapidapi_budget(budget: dict, n: int = 1) -> bool:
    """Local copy of RapidApiWatcher._spend() (rapidapi_engine.py) - same
    check-and-deduct logic, kept separate since instantiating the full
    Watcher here would also load players/build LineupModels for no reason.
    Shares the SAME rapidapi_budget.json file/BUDGET_CAP the live engine
    draws from - a closing-odds fetch here must never push total monthly
    usage over the cap."""
    if budget["calls_used"] + n > rapidapi_engine.BUDGET_CAP:
        return False
    budget["calls_used"] += n
    return True


def _fetch_closing_odds(fixture_id: str, clients: dict) -> tuple[float | None, float | None]:
    """Same-source closing-odds snapshot, fetched well after kickoff via
    whichever client originally produced this row's prediction - matching
    this project's "don't mix apples and oranges" CLV principle
    (backtest.py). (None, None) on ANY failure - a missing closing snapshot
    must never block grading the outcome itself."""
    try:
        if fixture_id.startswith("rapid_"):
            client = clients.get("rapidapi")
            budget = clients.get("rapidapi_budget")
            if client is None or budget is None:
                return None, None
            if not _spend_rapidapi_budget(budget):
                print(f"  ! rapidapi budget exhausted, skipping closing odds for {fixture_id}")
                return None, None
            event_id = int(fixture_id.removeprefix("rapid_"))
            resp = client.odds(event_id, countrycode=rapidapi_engine.ODDS_COUNTRYCODE)
            odds = rapidapi_engine._find_25_line(resp)
            rapidapi_engine._save_budget(budget)
            return odds
        elif fixture_id.startswith("sofa_"):
            client = clients.get("sofascore")
            if client is None:
                return None, None
            event_id = int(fixture_id.removeprefix("sofa_"))
            resp = client.odds(event_id)
            return sofascore_engine._find_25_line(resp)
        else:
            client = clients.get("apifootball")
            if client is None:
                return None, None
            resp = client.odds(int(fixture_id))
            return _best_over_under_odds(resp)
    except (RapidApiError, SofaScoreError, ApiFootballError) as e:
        print(f"  ! closing-odds fetch failed for {fixture_id}: {e}")
        return None, None
```

- [ ] **Step 4: Wire `clients` through `grade_row()` and compute `bet_clv`**

In `footymodel/live/grade_results.py`, find:

```python
def grade_row(row: pd.Series, cache: dict[str, list[dict]], client: ApiFootballClient) -> dict | None:
```

Replace with:

```python
def grade_row(row: pd.Series, cache: dict[str, list[dict]], clients: dict) -> dict | None:
```

Then find (two occurrences, both inside `grade_row`):

```python
        fx = client.fixture_by_id(int(row["fixture_id"]))
```

Replace with:

```python
        fx = clients["apifootball"].fixture_by_id(int(row["fixture_id"]))
```

And find:

```python
                fixtures = client.fixtures_by_date(date_str)
```

Replace with:

```python
                fixtures = clients["apifootball"].fixtures_by_date(date_str)
```

Then find:

```python
    return {
        "fixture_id": row["fixture_id"],
        "home": row["home"], "away": row["away"], "kickoff": row["kickoff"],
        "actual_home_goals": home_goals, "actual_away_goals": away_goals,
        "actual_total_goals": total_goals, "actual_over_won": actual_over_won,
        "model_p_over25": round(model_p_over25, 3), "model_correct": model_correct,
        "bet_side": bet_side, "bet_odds": bet_odds, "bet_won": bet_won,
        "realized_return": realized_return,
        "graded_at": pd.Timestamp.now().isoformat(),
    }
```

Replace with:

```python
    closing_odds_over25 = closing_odds_under25 = bet_clv = None
    if bet_side is not None:
        closing_odds_over25, closing_odds_under25 = _fetch_closing_odds(
            str(row["fixture_id"]), clients)
        closing_bet_odds = closing_odds_over25 if bet_side == "over" else closing_odds_under25
        if closing_bet_odds:
            bet_clv = round(bet_odds / closing_bet_odds - 1, 4)

    return {
        "fixture_id": row["fixture_id"],
        "home": row["home"], "away": row["away"], "kickoff": row["kickoff"],
        "actual_home_goals": home_goals, "actual_away_goals": away_goals,
        "actual_total_goals": total_goals, "actual_over_won": actual_over_won,
        "model_p_over25": round(model_p_over25, 3), "model_correct": model_correct,
        "bet_side": bet_side, "bet_odds": bet_odds, "bet_won": bet_won,
        "realized_return": realized_return,
        "closing_odds_over25": closing_odds_over25,
        "closing_odds_under25": closing_odds_under25,
        "bet_clv": bet_clv,
        "graded_at": pd.Timestamp.now().isoformat(),
    }
```

- [ ] **Step 5: Update `main()`'s client construction**

In `footymodel/live/grade_results.py`, find:

```python
    client = ApiFootballClient()
    cache: dict[str, list[dict]] = {}
    graded_rows = []
    for _, row in to_grade.iterrows():
        print(f"  grading {row['home']} v {row['away']} ({row['kickoff']})")
        result = grade_row(row, cache, client)
        if result is not None:
            graded_rows.append(result)
        else:
            print("    not gradeable yet (or out of API-Football's date-query window)")
```

Replace with:

```python
    fixture_ids = to_grade["fixture_id"].astype(str)
    clients: dict = {"apifootball": ApiFootballClient()}
    if fixture_ids.str.startswith("rapid_").any():
        clients["rapidapi"] = RapidApiClient()
        clients["rapidapi_budget"] = rapidapi_engine._load_budget()

    sofascore_client = None
    if fixture_ids.str.startswith("sofa_").any():
        sofascore_client = SofaScoreClient()
        clients["sofascore"] = sofascore_client

    cache: dict[str, list[dict]] = {}
    graded_rows = []
    try:
        for _, row in to_grade.iterrows():
            print(f"  grading {row['home']} v {row['away']} ({row['kickoff']})")
            result = grade_row(row, cache, clients)
            if result is not None:
                graded_rows.append(result)
            else:
                print("    not gradeable yet (or out of API-Football's date-query window)")
    finally:
        if sofascore_client is not None:
            sofascore_client.close()
```

- [ ] **Step 6: Run the test again and confirm it passes**

Run: `.venv/bin/python scripts/grade_results_clv_test.py`
Expected: ends with `ALL CHECKS PASSED — same-source closing-odds dispatch, shared RapidAPI budget accounting, and graceful degradation are all correct.`

- [ ] **Step 7: Migrate the existing `graded_results.csv` to the new column shape**

`graded_results.csv` is git-tracked (real production grading history, 6 rows) and is always read back with `pd.read_csv()` (header-based, not positional) — appending new rows with 3 extra columns via `to_csv(mode="a", header=False)` without first giving the EXISTING rows those same columns would silently misalign the file for every future reader. Run this once, from the repo root:

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_csv('data/processed/graded_results.csv')
for col in ('closing_odds_over25', 'closing_odds_under25', 'bet_clv'):
    if col not in df.columns:
        df[col] = pd.NA
df.to_csv('data/processed/graded_results.csv', index=False)
print(df.columns.tolist())
"
```

Expected: prints a column list ending in `..., 'closing_odds_over25', 'closing_odds_under25', 'bet_clv']`, and `data/processed/graded_results.csv` still has exactly 6 data rows (verify with `wc -l data/processed/graded_results.csv` → 7, header included), now with 3 additional empty columns.

- [ ] **Step 8: Sanity-check `main()` still imports and runs cleanly**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from footymodel.live import grade_results"`
Expected: no errors (confirms the new imports — `rapidapi_engine`, `sofascore_engine`, `RapidApiClient`, `SofaScoreClient`, `_best_over_under_odds` — all resolve correctly and nothing else in the file broke syntactically).

- [ ] **Step 9: Commit**

```bash
git add footymodel/live/grade_results.py scripts/grade_results_clv_test.py data/processed/graded_results.csv
git commit -m "feat: same-source closing-odds capture + CLV in grade_results.py"
```

---

### Task 2: Wire the new test into CI

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add the CI step**

In `.github/workflows/ci.yml`, find:

```yaml
      - name: Grade-results by-id lookup + fallback (pure, data-free)
        run: python scripts/grade_results_by_id_test.py
```

Replace with:

```yaml
      - name: Grade-results by-id lookup + fallback (pure, data-free)
        run: python scripts/grade_results_by_id_test.py
      - name: Grade-results closing-odds capture + CLV (pure, data-free)
        run: python scripts/grade_results_clv_test.py
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: wire grade_results_clv_test.py into CI"
```

---

## Post-plan verification

There is no immediate CLV verdict to report — this plan only makes the eventual analysis possible. The real check is that the NEXT scheduled grading run (`live_poll.yml`'s grading step, or a manual trigger) completes without error and produces at least one graded row with a non-null `closing_odds_over25`/`bet_clv` for a fixture that had a bet placed, confirming the new fetch genuinely works against the real API (not just the mocked test). Since API-Football is currently suspended, this real-world confirmation may need to wait until that account (or the `sian.agency`-based hedge source) is actually reachable again — note that as a known follow-up, not a blocker for merging this plan's code.
