"""Unit-check for notify_dashboard.py's build_goals_line(): confirms the
featured-fixture selection (the new prediction with the model's most
confident call - largest distance from a 50/50 split) and the one-fixture
vs multi-fixture body format. Pure/data-free - synthetic row dicts only, no
git diff or network involved, safe to run in CI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from notify_dashboard import build_goals_line

# --- one fixture ---
one = [{"home": "Chelsea", "away": "Brighton", "model_p_over25": "0.439", "exp_total_goals": "2.43"}]
line = build_goals_line(one)
print(line)
assert line == "Chelsea v Brighton: 44% O2.5, xG 2.43", line

# --- multiple fixtures: the one furthest from 50% should be featured, not
# just the first in the list (Sunderland v Fulham at 0.360 is 14 points
# from 50%, more than Chelsea's 6.1 or Leeds' 5.2). ---
many = [
    {"home": "Leeds", "away": "Brentford", "model_p_over25": "0.552", "exp_total_goals": "2.89"},
    {"home": "Chelsea", "away": "Brighton", "model_p_over25": "0.439", "exp_total_goals": "2.43"},
    {"home": "Sunderland", "away": "Fulham", "model_p_over25": "0.360", "exp_total_goals": "2.14"},
]
line2 = build_goals_line(many)
print(line2)
assert line2 == "Sunderland v Fulham: 36% O2.5, xG 2.14 (+2 more)", (
    f"expected the fixture furthest from 50% (Sunderland v Fulham) to be featured, got: {line2}"
)

print("ALL CHECKS PASSED — featured-fixture selection and body format are correct.")
