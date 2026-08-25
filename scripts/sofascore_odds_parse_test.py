"""Unit-check for the SofaScore fractional-odds conversion and 2.5-line
market lookup (sofascore_engine.py), using the REAL market shape confirmed
against the live site (2026-08-26, Real Madrid v Real Sociedad). Pure/
data-free - no scraped datasets needed, so this is safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.sofascore_engine import _find_25_line, _frac_to_decimal

assert abs(_frac_to_decimal("4/9") - 1.4444444444444444) < 1e-9
assert abs(_frac_to_decimal("7/4") - 2.75) < 1e-9
assert abs(_frac_to_decimal("1/1") - 2.0) < 1e-9  # evens

markets = [
    {"marketGroup": "Match goals", "choiceGroup": "1.5", "choices": [
        {"name": "Over", "fractionalValue": "1/7"},
        {"name": "Under", "fractionalValue": "9/2"},
    ]},
    {"marketGroup": "Match goals", "choiceGroup": "2.5", "choices": [
        {"name": "Over", "fractionalValue": "4/9"},
        {"name": "Under", "fractionalValue": "7/4"},
    ]},
    {"marketGroup": "1X2", "choiceGroup": None, "choices": [
        {"name": "1", "fractionalValue": "11/5"},
    ]},
]

over, under = _find_25_line(markets)
assert abs(over - 1.4444444444444444) < 1e-9, "should pick the 2.5 choiceGroup, not 1.5"
assert abs(under - 2.75) < 1e-9

# No "Match goals" market at all (e.g. suspended/unavailable) -> (None, None),
# not a crash.
none_over, none_under = _find_25_line([{"marketGroup": "1X2", "choiceGroup": None, "choices": []}])
assert none_over is None and none_under is None

print("sofascore_odds_parse_test: OK")
