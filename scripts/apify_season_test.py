"""Unit test for Apify season resolution (no API call)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.apify_engine import _season_label, _season_start_year

import pandas as pd

assert _season_start_year(pd.Timestamp("2026-09-06", tz="UTC")) == 2026
assert _season_label(2026) == "26/27"
assert _season_start_year(pd.Timestamp("2026-06-01", tz="UTC")) == 2025
assert _season_label(2025) == "25/26"
print("apify_season_test: OK")
