"""Unit-check for the goals engine's Over/Under 2.5 odds parser
(engine.py's _best_over_under_odds), using the REAL bet name confirmed
against a live API-Football key (2026-08-27): the market is named
"Goals Over/Under", not "Over/Under" - a prior mismatch here (fixed
2026-08-27) meant odds_over25/odds_under25 silently stayed empty on every
single logged prediction for weeks, with no error anywhere. Pure/data-free -
safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.engine import _best_over_under_odds

odds_response = [{"bookmakers": [
    {"name": "10Bet", "bets": [
        {"name": "Match Winner", "values": [{"value": "Home", "odd": "1.50"}]},
        {"name": "Goals Over/Under", "values": [
            {"value": "Over 1.5", "odd": "1.42"},
            {"value": "Under 1.5", "odd": "2.80"},
            {"value": "Over 2.5", "odd": "2.25"},
            {"value": "Under 2.5", "odd": "1.62"},
        ]},
    ]},
    {"name": "Bet365", "bets": [
        {"name": "Goals Over/Under", "values": [
            {"value": "Over 2.5", "odd": "2.30"},
            {"value": "Under 2.5", "odd": "1.60"},
        ]},
        # A differently-named market that must NOT be mistaken for the
        # real one - this is exactly the shape of the original bug
        # (checking for "Over/Under" literally, which never matches).
        {"name": "Goals Over/Under First Half", "values": [
            {"value": "Over 0.5", "odd": "1.30"},
        ]},
    ]},
]}]

over, under = _best_over_under_odds(odds_response)
assert over == 2.30, f"expected best (max) Over 2.5 = 2.30 across bookmakers, got {over}"
assert under == 1.62, f"expected best (max) Under 2.5 = 1.62 across bookmakers, got {under}"

# No "Goals Over/Under" market anywhere -> (None, None), not a crash.
none_over, none_under = _best_over_under_odds(
    [{"bookmakers": [{"bets": [{"name": "Match Winner", "values": []}]}]}])
assert none_over is None and none_under is None

print("goals_odds_parse_test: OK")
