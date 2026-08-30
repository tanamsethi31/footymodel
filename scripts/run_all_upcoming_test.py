"""Unit-check for run_all.py's build_upcoming_list() - shapes API-Football
fixture dicts into the small preview record the dashboard shows for matches
that don't have a confirmed-lineup prediction yet (fixture_id, home, away,
kickoff only - no lineup/odds/model data, since none of that exists yet for
these fixtures). Doesn't check confirmation status itself - the dashboard
does that by cross-referencing fixture_id against what it already has.
Pure/data-free - safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live.run_all import build_upcoming_list

api_id_to_div = {39: "E0"}
now = pd.Timestamp("2026-08-30T00:00:00+00:00")

fixtures = [
    {
        "fixture": {"id": 111, "date": "2026-08-30T13:00:00+00:00"},
        "league": {"id": 39},
        "teams": {"home": {"name": "Chelsea"}, "away": {"name": "Brighton"}},
    },
    {
        "fixture": {"id": 222, "date": "2026-08-30T15:00:00+00:00"},
        "league": {"id": 140},  # La Liga - not a tracked league
        "teams": {"home": {"name": "Barcelona"}, "away": {"name": "Real Madrid"}},
    },
    {
        # Already kicked off - never got a confirmed lineup, so never made
        # it into `seen` either. Without an explicit kickoff filter this
        # would render as "analysis pending" forever.
        "fixture": {"id": 333, "date": "2026-08-29T13:00:00+00:00"},
        "league": {"id": 39},
        "teams": {"home": {"name": "Liverpool"}, "away": {"name": "Everton"}},
    },
]

result = build_upcoming_list(fixtures, api_id_to_div, now)
assert result == [
    {"fixture_id": 111, "home": "Chelsea", "away": "Brighton",
     "kickoff": "2026-08-30T13:00:00+00:00"},
], result
assert len(result) == 1, (
    "expected only the tracked-league, still-upcoming fixture - "
    "the untracked league and the already-kicked-off fixture must both be excluded"
)

assert build_upcoming_list([], api_id_to_div, now) == []

print("run_all_upcoming_test: OK")
