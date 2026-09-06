"""Grade result lookup helpers (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live.grade_results import _parse_apify_scores

finished = [{
    "homeScore": 2,
    "awayScore": 1,
    "matchStatus": "Ended",
    "rawStatus": {"type": "finished"},
}]
assert _parse_apify_scores(finished) == (2, 1)
assert _parse_apify_scores([{"homeScore": 1, "awayScore": 0, "matchStatus": "Live"}]) is None

print("grade_results_apify_test: OK")
