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
# Also stub fixtures_by_date: grade_row's PRE-EXISTING (unchanged by this
# task) date+fuzzy-name outcome fallback runs for any fixture_id that
# int()-fails (i.e. every rapid_/sofa_-prefixed row below), regardless of
# which live source originally logged the prediction - see the module
# docstring. Without this, those rows' match OUTCOME lookup itself returns
# None before ever reaching the new closing-odds/bet_clv code this test
# is actually meant to exercise.
mock_apifootball.fixtures_by_date.return_value = [finished_fixture]
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
