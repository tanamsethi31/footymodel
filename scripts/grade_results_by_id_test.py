"""Unit-check for grade_results.py's grade_row(): confirms it looks a
fixture up directly by id first (not subject to the free tier's rolling
date-query window), and only falls back to the date+fuzzy-name lookup for
a non-API-Football fixture_id (RapidAPI/SofaScore's own prefixed formats).
Pure/data-free (mocked client) - safe to run in CI."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live.grade_results import grade_row

finished_fixture = {
    "fixture": {"id": 1557379, "status": {"short": "FT"}},
    "league": {"id": 39},  # E0 - only read by the date+fuzzy-name fallback path
    "teams": {"home": {"name": "Chelsea"}, "away": {"name": "Brighton"}},
    "goals": {"home": 1, "away": 2},
}

# --- Plain API-Football fixture_id: graded via fixture_by_id, never
# touches fixtures_by_date at all. ---
mock_client = MagicMock()
mock_client.fixture_by_id.return_value = finished_fixture

row = pd.Series({
    "fixture_id": "1557379", "home": "Chelsea", "away": "Brighton",
    "kickoff": "2026-08-30T13:00:00+00:00", "model_p_over25": 0.439,
    "ev_over25": float("nan"), "ev_under25": float("nan"), "odds_over25": None, "odds_under25": None,
})
result = grade_row(row, {}, {"apifootball": mock_client})

print(f"fixture_by_id calls: {mock_client.fixture_by_id.call_count} (expect 1)")
print(f"fixtures_by_date calls: {mock_client.fixtures_by_date.call_count} (expect 0)")
assert mock_client.fixture_by_id.call_count == 1
assert mock_client.fixtures_by_date.call_count == 0, (
    "a plain API-Football fixture_id must be graded via fixture_by_id, never the date-based fallback"
)
assert result is not None
assert result["actual_home_goals"] == 1 and result["actual_away_goals"] == 2
assert result["actual_over_won"] is True  # 3 total goals > 2.5

# --- Non-API-Football fixture_id (RapidAPI-style prefix): fixture_by_id
# raises ValueError internally (int("rapid_123") fails) - falls back to the
# date+fuzzy-name path. ---
mock_client2 = MagicMock()
mock_client2.fixtures_by_date.return_value = [finished_fixture]

row2 = pd.Series({
    "fixture_id": "rapid_5868013", "home": "Chelsea", "away": "Brighton",
    "kickoff": "2026-08-30T13:00:00+00:00", "model_p_over25": 0.439,
    "ev_over25": float("nan"), "ev_under25": float("nan"), "odds_over25": None, "odds_under25": None,
})
cache = {}
result2 = grade_row(row2, cache, {"apifootball": mock_client2})

print(f"fixtures_by_date calls (fallback path): {mock_client2.fixtures_by_date.call_count} (expect 1)")
assert mock_client2.fixture_by_id.call_count == 0, "a prefixed fixture_id must never reach fixture_by_id"
assert mock_client2.fixtures_by_date.call_count == 1
assert result2 is not None
assert result2["actual_home_goals"] == 1 and result2["actual_away_goals"] == 2

print("ALL CHECKS PASSED — by-id lookup used for plain fixture_ids, "
      "date+fuzzy-name fallback used for prefixed (RapidAPI/SofaScore) ones.")
