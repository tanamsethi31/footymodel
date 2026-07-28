"""Unit-check for Asian Handicap settlement (Phase C2), before it feeds the
backtest. Verifies _ah_home_outcome() against hand-computed examples for
whole, half, and quarter lines — including push and half-win/half-loss cases.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from footymodel.model import _ah_home_outcome

# (margin, line, expected_home_outcome, description)
CASES = [
    # --- whole lines: push possible ---
    (2, -2.0, 0.0, "whole line exact push (City 2-0 Forest, line -2.0)"),
    (3, -2.0, 1.0, "whole line full win (won by more than the line)"),
    (1, -2.0, -1.0, "whole line full loss (won by less than the line)"),
    (0, 0.0, 0.0, "pick'em draw = push"),
    (1, 0.0, 1.0, "pick'em home win = win"),
    (-1, 0.0, -1.0, "pick'em home loss = loss"),
    # --- half lines: never push ---
    (1, -1.5, -1.0, "half line: won by 1, needed 1.5+ -> full loss"),
    (2, -1.5, 1.0, "half line: won by 2, covers 1.5 -> full win"),
    (0, 1.5, 1.0, "half line: away favoured, home draw covers +1.5 -> full win"),
    # --- quarter lines: split stake -> half win/half loss, no true push ---
    (1, -0.75, 0.5, "quarter -0.75: won by 1 -> half win (push+win averaged)"),
    (0, -0.75, -1.0, "quarter -0.75: draw -> full loss (real AH rule)"),
    (-1, -0.75, -1.0, "quarter -0.75: lost by 1 -> full loss"),
    (2, -0.75, 1.0, "quarter -0.75: won by 2 -> full win"),
    (-1, 1.25, 0.5, "quarter +1.25 (home underdog): lost by 1 -> half win"),
    (-2, 1.25, -1.0, "quarter +1.25: lost by 2 -> full loss (both sublines negative)"),
    (-1, 0.75, -0.5, "quarter +0.75: lost by 1 -> half loss (push+loss averaged)"),
]

print(f"{'margin':>6} {'line':>6} {'expected':>9} {'actual':>7}  result")
print("-" * 60)
n_fail = 0
for margin, line, expected, desc in CASES:
    actual = float(_ah_home_outcome(np.array(margin), line))
    ok = np.isclose(actual, expected)
    n_fail += not ok
    print(f"{margin:>6} {line:>6.2f} {expected:>9.2f} {actual:>7.2f}  "
          f"{'OK' if ok else 'FAIL'}  {desc}")

# Away side must always be the exact mirror of home's outcome.
print("\nAway-mirror check (away_outcome == -home_outcome):")
for margin, line, expected, desc in CASES[:6]:
    h = float(_ah_home_outcome(np.array(margin), line))
    a = float(_ah_home_outcome(np.array(-margin), -line))  # away's own perspective
    ok = np.isclose(a, -h)
    n_fail += not ok
    print(f"  margin={margin:+d} line={line:+.2f}: home={h:+.2f} away={a:+.2f}  "
          f"{'OK' if ok else 'FAIL'}")

print(f"\n{'ALL CHECKS PASSED' if n_fail == 0 else f'{n_fail} CHECK(S) FAILED'}")
sys.exit(1 if n_fail else 0)
