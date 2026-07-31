"""Unit-check for the Phase I player-prop odds parser (shots_engine.py), using
the REAL bookmaker value shape confirmed against a live API-Football key
(2026-07-31): "{player} - N+" lines under "Player Shots On Target" and
"Home/Away Player Shots". Pure/data-free - no scraped datasets needed, so this
is safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.shots_engine import _lookup_player_odd, _parse_player_line_odds

odds_response = [{"bookmakers": [{"bets": [
    {"name": "Home Player Shots", "values": [
        {"value": "Erling Haaland - 1+", "odd": "1.40"},
        {"value": "Erling Haaland - 2+", "odd": "2.20"},
        {"value": "Erling Haaland - 3+", "odd": "5.00"},
    ]},
    {"name": "Player Shots On Target", "values": [
        {"value": "Erling Haaland - 1+", "odd": "1.65"},
        {"value": "Erling Haaland - 2+", "odd": "3.75"},
    ]},
    # A market intentionally NOT in the parser's allow-list (team total, not
    # per-player) - must be ignored rather than mis-parsed.
    {"name": "Away Player Shots Total", "values": [
        {"value": "Over 3.5", "odd": "1.29"},
    ]},
]}]}]

shots_odds = _parse_player_line_odds(odds_response, {"Home Player Shots", "Away Player Shots"})
sot_odds = _parse_player_line_odds(odds_response, {"Player Shots On Target"})

assert shots_odds[("erling haaland", 0.5)] == 1.40, "N=1+ should map to line 0.5"
assert shots_odds[("erling haaland", 1.5)] == 2.20, "N=2+ should map to line 1.5"
assert shots_odds[("erling haaland", 2.5)] == 5.00, "N=3+ should map to line 2.5"
assert sot_odds[("erling haaland", 0.5)] == 1.65
assert ("over", 3.5) not in shots_odds, "team-total market must not leak into per-player odds"
assert len(shots_odds) == 3, "the team-total market should not have contributed any entries"

# Exact match
assert _lookup_player_odd(shots_odds, "Erling Haaland", 0.5) == 1.40
# Fuzzy fallback (spelling drift between the lineup feed and the odds feed)
assert _lookup_player_odd(shots_odds, "E. Haaland", 0.5) == 1.40
# No match at an unseen line
assert _lookup_player_odd(shots_odds, "Erling Haaland", 3.5) is None
# No match for an unrelated name
assert _lookup_player_odd(shots_odds, "Random Nobody", 0.5) is None

print("ALL CHECKS PASSED")
