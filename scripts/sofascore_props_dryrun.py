"""Model-only props row builder for a mocked SofaScore lineup (no network)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live import namematch
from footymodel.live.sofascore_props_engine import SofaScorePropsWatcher
from footymodel.players import load_players

players = load_players()
home_us, away_us = "Manchester City", "Everton"
home_names = list(namematch.team_roster_index(players, "E0", home_us).keys())[:11]
away_names = list(namematch.team_roster_index(players, "E0", away_us).keys())[:11]

event = {
    "id": 888001,
    "startTimestamp": int((pd.Timestamp.now(tz="UTC") + pd.Timedelta(minutes=30)).timestamp()),
    "homeTeam": {"name": home_us},
    "awayTeam": {"name": away_us},
    "status": {"type": "notstarted"},
}

mock_client = MagicMock()
mock_client.lineups.return_value = {
    "confirmed": True,
    "home": {"players": [{"player": {"name": n}, "substitute": False} for n in home_names]},
    "away": {"players": [{"player": {"name": n}, "substitute": False} for n in away_names]},
}

rows = SofaScorePropsWatcher(mock_client).process_event("E0", event)
assert rows and len(rows) == 22, f"expected 22 rows, got {len(rows or [])}"
assert rows[0]["fixture_id"] == "sofa_888001"
assert rows[0]["home"] == home_us
print("sofascore_props_dryrun: OK")
