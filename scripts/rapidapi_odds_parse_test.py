"""Unit-check for the RapidAPI (Free API Live Football Data) odds-market
lookup (rapidapi_engine.py), using the REAL response shape confirmed
against the live API (2026-08-27, Real Madrid v Real Sociedad,
countrycode=DE). Pure/data-free - no scraped datasets needed, so this is
safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.rapidapi_engine import _find_25_line

real_response = {
    "odds": {
        "odds": {
            "oddsTabMarkets": [
                {"category": "Bets", "markets": [
                    {"header": "1x2", "selections": [
                        {"name": "1", "oddsDecimal": "1.30"},
                    ]},
                    {"header": "Total goals over/under", "selections": [
                        {"name": "Over 2.5", "oddsDecimal": "1.43"},
                        {"name": "Under 2.5", "oddsDecimal": "2.75"},
                    ]},
                ]},
            ]
        }
    }
}

over, under = _find_25_line(real_response)
assert over == 1.43, f"expected 1.43, got {over}"
assert under == 2.75, f"expected 2.75, got {under}"

# No "over/under" market present at all (e.g. countrycode with no coverage
# for this fixture) -> (None, None), not a crash.
none_over, none_under = _find_25_line({"odds": {"odds": {"oddsTabMarkets": [
    {"category": "Bets", "markets": [{"header": "1x2", "selections": []}]},
]}}})
assert none_over is None and none_under is None

# Missing keys entirely (malformed/empty response) -> also (None, None).
empty_over, empty_under = _find_25_line({})
assert empty_over is None and empty_under is None

print("rapidapi_odds_parse_test: OK")
