"""Unit-check for Apify football-api-scraper match-goals odds parsing
(apify_engine.py), using the REAL response shape from matchId 14023948
(Fulham v Bournemouth, verified 2026-09-04 via Apify MCP). Pure/data-free."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.apify_engine import _find_25_line, _parse_lineups

# Subset of real matchOdds rows — eight "Match goals" markets, 2.5 ~= row 3.
real_odds = [
    {
        "marketGroup": "Match goals",
        "oddsChoices": [
            {"outcome": "Over", "fractionalValue": "1/33"},
            {"outcome": "Under", "fractionalValue": "14/1"},
        ],
    },
    {
        "marketGroup": "Match goals",
        "oddsChoices": [
            {"outcome": "Over", "fractionalValue": "1/5"},
            {"outcome": "Under", "fractionalValue": "7/2"},
        ],
    },
    {
        "marketGroup": "Match goals",
        "oddsChoices": [
            {"outcome": "Over", "fractionalValue": "8/13"},
            {"outcome": "Under", "fractionalValue": "13/10"},
        ],
    },
    {
        "marketGroup": "Match goals",
        "oddsChoices": [
            {"outcome": "Over", "fractionalValue": "6/4"},
            {"outcome": "Under", "fractionalValue": "8/15"},
        ],
    },
]

over, under = _find_25_line(real_odds)
assert over is not None and under is not None
assert 1.5 < over < 2.0, f"expected main-line over near 1.6, got {over}"
assert 2.0 < under < 2.5, f"expected main-line under near 2.3, got {under}"

lineup_rows = [
    {"lineupConfirmed": True, "lineupSide": "home", "playerName": "Bernd Leno", "isSubstitute": False},
    {"lineupConfirmed": True, "lineupSide": "away", "playerName": "Neto", "isSubstitute": False},
    {"lineupConfirmed": True, "lineupSide": "home", "playerName": "Sub", "isSubstitute": True},
]
parsed = _parse_lineups(lineup_rows)
assert parsed["confirmed"] is True
assert parsed["home"] == ["Bernd Leno"]
assert parsed["away"] == ["Neto"]

assert _find_25_line([]) == (None, None)

print("apify_odds_parse_test: OK")
