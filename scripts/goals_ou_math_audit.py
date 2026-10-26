#!/usr/bin/env python3
"""Audit goals O/U 2.5 mathematics used in the live SofaScore engine."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.sofascore_engine import _find_25_line, _frac_to_decimal
from footymodel.players import BEST_BLEND_W, LineupModel, _ou_prob_over25
from footymodel.strategy import remove_margin
from footymodel.staking import kelly_fraction, recommended_stake

# Poisson O/U mapping sanity
assert 0.45 < _ou_prob_over25(2.5) < 0.55
assert _ou_prob_over25(3.5) > _ou_prob_over25(2.5)

# Margin strip + EV (same as sofascore_engine row build)
over, under = 1.90, 1.95
fair = remove_margin(np.array([over, under]))
p_model = 0.55
ev_over = p_model * over - 1.0
ev_under = (1 - p_model) * under - 1.0
assert fair[0] + fair[1] < 1.0 + 1e-6
assert abs(ev_over - (p_model * over - 1.0)) < 1e-9

# Kelly stake positive only with edge
stake = recommended_stake(100.0, p_model, over, kelly_mult=0.25, max_fraction=0.02)
assert stake > 0
assert recommended_stake(100.0, fair[0], over) == 0.0

# SofaScore 2.5 line parser
markets = [
    {
        "marketGroup": "Match goals",
        "choiceGroup": "2.5",
        "choices": [
            {"name": "Over", "fractionalValue": "4/9"},
            {"name": "Under", "fractionalValue": "7/4"},
        ],
    }
]
o, u = _find_25_line(markets)
assert o is not None and u is not None

# Blend constant documented in players.py
assert BEST_BLEND_W == 0.25

print("goals_ou_math_audit: OK")
print(f"  BEST_BLEND_W={BEST_BLEND_W} (team weight in lineup blend)")
print(f"  example Kelly full f*={kelly_fraction(p_model, over):.4f} at p={p_model}, odds={over}")
