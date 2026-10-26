"""Unit-check SofaScore player shots/SOT odds parsing (synthetic market shapes)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.sofascore_props_odds import parse_sofascore_player_prop_odds

markets = [
    {
        "marketGroup": "Player shots",
        "marketName": "Player shots",
        "choiceGroup": "1.5",
        "choices": [
            {"name": "Erling Haaland", "fractionalValue": "4/5"},
            {"name": "Phil Foden", "fractionalValue": "2/1"},
        ],
    },
    {
        "marketGroup": "Player shots on target",
        "choiceGroup": "0.5",
        "choices": [
            {"name": "Erling Haaland", "fractionalValue": "4/6"},
        ],
    },
    {
        "marketGroup": "Home team shots",
        "choiceGroup": "2.5",
        "choices": [{"name": "Over", "fractionalValue": "5/6"}],
    },
    {
        "marketGroup": "Player specials",
        "choices": [
            {"name": "Bukayo Saka - 1+", "fractionalValue": "1/2"},
            {"name": "Bukayo Saka - 2+", "fractionalValue": "6/4"},
        ],
    },
]

shots, sot = parse_sofascore_player_prop_odds(markets)
assert ("erling haaland", 1.5) in shots
assert abs(shots[("erling haaland", 1.5)] - 1.8) < 1e-9
assert ("erling haaland", 0.5) in sot
assert ("bukayo saka", 0.5) in shots
assert ("bukayo saka", 1.5) in shots
assert ("over", 2.5) not in shots
print("sofascore_props_odds_test: OK")
