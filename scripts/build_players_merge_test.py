"""Unit-check for build_players.py's merge_player_dataset() - it replaces just
the (league, season) pairs being re-scraped in the existing player_match.parquet,
leaving every other league-season row untouched. This is what makes it safe to
run a targeted daily refresh (e.g. just the current season) without silently
losing every other season's already-scraped rows, or without needing to
re-scrape the entire multi-season history (thousands of per-match Understat
requests) every single day. Pure/data-free - safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from scripts.build_players import merge_player_dataset

existing = pd.DataFrame([
    {"match_id": 1, "league": "E0", "season": "2024/25", "player_id": "p1"},
    {"match_id": 2, "league": "E0", "season": "2025/26", "player_id": "p2"},  # stale, being refreshed
    {"match_id": 3, "league": "SP1", "season": "2025/26", "player_id": "p3"},  # different league, untouched
])
new_rows = pd.DataFrame([
    {"match_id": 4, "league": "E0", "season": "2025/26", "player_id": "p4"},  # fresh replacement
])

merged = merge_player_dataset(existing, new_rows, divs=["E0"], years=[2025])
assert set(merged["match_id"]) == {1, 3, 4}, (
    "expected: keep E0 2024/25 (1), keep SP1 2025/26 (3, different league), "
    f"drop stale E0 2025/26 (2), add fresh E0 2025/26 (4) - got {sorted(merged['match_id'])}"
)

# No prior file (first run) - just returns new_rows as-is, nothing to merge.
first_run = merge_player_dataset(None, new_rows, divs=["E0"], years=[2025])
assert first_run.equals(new_rows)

print("build_players_merge_test: OK")
