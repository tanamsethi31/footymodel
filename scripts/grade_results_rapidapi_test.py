"""Grade result lookup helpers for RapidAPI (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.grade_results import _parse_rapidapi_scores

finished = {
    "id": 5795438,
    "home": {"name": "Everton", "score": 2},
    "away": {"name": "Man United", "score": 1},
    "status": {"finished": True, "reason": {"short": "FT"}},
}
assert _parse_rapidapi_scores(finished) == (2, 1)

score_str = {
    "home": {"name": "A"},
    "away": {"name": "B"},
    "status": {"finished": True, "scoreStr": "3 - 0"},
}
assert _parse_rapidapi_scores(score_str) == (3, 0)

live = {
    "home": {"name": "A", "score": 1},
    "away": {"name": "B", "score": 0},
    "status": {"finished": False, "reason": {"short": "LIVE"}},
}
assert _parse_rapidapi_scores(live) is None

print("grade_results_rapidapi_test: OK")
