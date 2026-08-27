"""Unit-check for grade_results.py's kickoff-timestamp parsing. The three
live engines log kickoff in different ISO 8601 variants (API-Football:
"...+00:00", SofaScore/RapidAPI: "...Z" with milliseconds) - pandas'
to_datetime silently produces NaT on a MIXED-format series unless told
format="mixed" (confirmed directly, 2026-08-27: without it, every
RapidAPI-sourced row's age came out NaN, so it would never get graded, no
error raised anywhere). Pure/data-free - safe to run in CI.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

mixed = pd.Series([
    "2026-08-23T13:00:00+00:00",  # API-Football style
    "2026-08-27T18:30:00.000Z",   # SofaScore/RapidAPI style
])

parsed = pd.to_datetime(mixed, utc=True, format="mixed", errors="coerce")
assert parsed.notna().all(), "mixed-format kickoff timestamps must all parse, not silently NaT"
assert parsed[0] == pd.Timestamp("2026-08-23T13:00:00", tz="UTC")
assert parsed[1] == pd.Timestamp("2026-08-27T18:30:00", tz="UTC")

# The bug this guards against: the SAME series without format="mixed"
# drops the second (differently-formatted) row to NaT.
without_mixed = pd.to_datetime(mixed, utc=True, errors="coerce")
assert without_mixed.isna().any(), (
    "if this now passes, pandas' default mixed-format handling changed - "
    "the format='mixed' fix in grade_results.py may no longer be necessary, "
    "but don't remove it without re-verifying against a real ragged log"
)

print("grade_results_datetime_test: OK")
