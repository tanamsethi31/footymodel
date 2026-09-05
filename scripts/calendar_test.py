"""Pure checks for the saved PL fixture calendar (gating, upcoming merge,
date-bucket expansion). No network, no quota.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live import calendar as fxcal
from footymodel.live.client import ApiFootballError

tmp = Path(tempfile.mkdtemp())
fxcal.CALENDAR_FILE = tmp / "fixture_calendar.json"
fxcal.UPCOMING_LOG = tmp / "upcoming_fixtures.json"
fxcal.UNDERSTAT_DIR = tmp

NOW = pd.Timestamp("2026-09-03T12:00:00+00:00")


def _payload(fixtures, refreshed_at="2026-09-03T11:00:00+00:00"):
    return {"refreshed_at": refreshed_at, "horizon_days": 10, "fixtures": fixtures}


WEEKEND = {
    "fixture_id": 1558001,
    "league_id": 39,
    "home": "Arsenal",
    "away": "Chelsea",
    "kickoff": "2026-09-12T14:00:00+00:00",
}
LIVE_SOON = {
    "fixture_id": 1558002,
    "league_id": 39,
    "home": "Liverpool",
    "away": "Everton",
    "kickoff": "2026-09-03T13:30:00+00:00",  # 90 min from NOW
}
YESTERDAY = {
    "fixture_id": 1558003,
    "league_id": 39,
    "home": "Leeds",
    "away": "Brentford",
    "kickoff": "2026-09-02T15:00:00+00:00",  # 21h ago — inside 24h behind
}


# --- freshness / fail-open ---------------------------------------------------
assert fxcal.load_calendar() is None
assert fxcal.calendar_is_fresh(NOW) is False
assert fxcal.should_run_live_engines(NOW, seen=set()) is True, (
    "missing calendar must fail open"
)

fxcal.save_calendar(_payload([WEEKEND], refreshed_at="2026-09-01T00:00:00+00:00"))
assert fxcal.calendar_is_fresh(NOW) is False, "36h+ snapshot is stale"
assert fxcal.should_run_live_engines(NOW, seen=set()) is True, (
    "stale calendar must fail open"
)

fresh = _payload([WEEKEND])
fxcal.save_calendar(fresh)
assert fxcal.calendar_is_fresh(NOW, payload=fresh) is True
assert fxcal.should_run_live_engines(NOW, seen=set(), payload=fresh) is False, (
    "fresh calendar with nothing in the live window should skip engines"
)

empty_fresh = _payload([], refreshed_at="2026-09-03T11:00:00+00:00")
fxcal.save_calendar(empty_fresh)
assert fxcal.should_run_live_engines(NOW, seen=set(), payload=empty_fresh) is True, (
    "fresh but empty calendar must fail open"
)


# --- live window -------------------------------------------------------------
in_window = fxcal.fixtures_in_live_window(NOW, _payload([WEEKEND, LIVE_SOON, YESTERDAY]))
ids = {r["fixture_id"] for r in in_window}
assert ids == {1558002, 1558003}, ids
assert 1558001 not in ids, "next weekend is outside the 2h-ahead window"


# --- skip when already seen; run when unseen ---------------------------------
payload_live = _payload([LIVE_SOON])
assert fxcal.should_run_live_engines(NOW, seen={1558002}, payload=payload_live) is False
assert fxcal.should_run_live_engines(NOW, seen=set(), payload=payload_live) is True
assert fxcal.should_run_live_engines(NOW, seen={"1558002"}, payload=payload_live) is False, (
    "seen-set entries may be strings from JSON"
)


# --- upcoming preview: future only, sorted -----------------------------------
upcoming = fxcal.upcoming_from_calendar(NOW, _payload([YESTERDAY, WEEKEND, LIVE_SOON]))
assert [r["fixture_id"] for r in upcoming] == [1558002, 1558001], upcoming
assert YESTERDAY["fixture_id"] not in {r["fixture_id"] for r in upcoming}

written = fxcal.write_upcoming_from_calendar(NOW, _payload([WEEKEND]))
assert json.loads(fxcal.UPCOMING_LOG.read_text()) == written
assert written == [{"fixture_id": 1558001, "home": "Arsenal", "away": "Chelsea",
                    "kickoff": WEEKEND["kickoff"]}]


# --- merge: live fetch wins on the same id -----------------------------------
cal_row = {"fixture_id": 1, "home": "A", "away": "B", "kickoff": "2026-09-12T14:00:00+00:00"}
live_row = {"fixture_id": 1, "home": "Arsenal", "away": "Chelsea",
            "kickoff": "2026-09-12T16:30:00+00:00"}  # KO moved
extra = {"fixture_id": 2, "home": "C", "away": "D", "kickoff": "2026-09-13T14:00:00+00:00"}
merged = fxcal.merge_upcoming([live_row], [cal_row, extra])
assert merged[0]["kickoff"] == live_row["kickoff"], merged
assert [r["fixture_id"] for r in merged] == [1, 2]


# --- date buckets: default 3 days + yesterday from calendar ------------------
default_dates = fxcal.date_buckets_to_fetch(NOW, _payload([WEEKEND]))
assert default_dates == {"2026-09-03", "2026-09-04", "2026-09-05"}, default_dates

with_yesterday = fxcal.date_buckets_to_fetch(NOW, _payload([YESTERDAY]))
assert "2026-09-02" in with_yesterday, with_yesterday
assert with_yesterday == {"2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05"}


# --- refresh: filters to tracked leagues, writes calendar + upcoming ---------
mock = MagicMock()
def _by_date(date_str):
    if date_str == "2026-09-12":
        return [
            {"league": {"id": 39},
             "fixture": {"id": 1558001, "date": WEEKEND["kickoff"]},
             "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}}},
            {"league": {"id": 140},  # La Liga — not tracked
             "fixture": {"id": 99, "date": "2026-09-12T19:00:00+00:00"},
             "teams": {"home": {"name": "Barca"}, "away": {"name": "Madrid"}}},
        ]
    if date_str == "2026-09-03":
        raise ApiFootballError("transient")
    return []
mock.fixtures_by_date.side_effect = _by_date

refreshed = fxcal.refresh_calendar(mock, now=NOW, horizon_days=10)
assert mock.fixtures_by_date.call_count == 11  # 0..10 inclusive
assert [f["fixture_id"] for f in refreshed["fixtures"]] == [1558001]
assert json.loads(fxcal.CALENDAR_FILE.read_text())["fixtures"][0]["home"] == "Arsenal"
assert json.loads(fxcal.UPCOMING_LOG.read_text())[0]["fixture_id"] == 1558001

# --- Understat fills the dashboard list when the API calendar is empty ------
us_payload = {
    "dates": [
        {"id": "31200", "isResult": False,
         "h": {"title": "Ipswich"}, "a": {"title": "Liverpool"},
         "datetime": "2026-09-04 19:00:00"},
        {"id": "31180", "isResult": True,
         "h": {"title": "Arsenal"}, "a": {"title": "Coventry"},
         "datetime": "2026-09-21 19:00:00"},
        {"id": "31999", "isResult": False,
         "h": {"title": "Too"}, "a": {"title": "Far"},
         "datetime": "2026-10-01 15:00:00"},
        {"id": "31201", "isResult": False,
         "h": {"title": "Newcastle United"}, "a": {"title": "Bournemouth"},
         "datetime": "2026-09-05 11:30:00"},
    ]
}
(fxcal.UNDERSTAT_DIR / "EPL_2026.json").write_text(json.dumps(us_payload))
us_rows = fxcal.upcoming_from_understat(NOW, horizon_days=10, year=2026)
assert [r["fixture_id"] for r in us_rows] == ["us_31200", "us_31201"], us_rows
assert us_rows[0]["home"] == "Ipswich"

# Same match from the API calendar wins over the Understat placeholder.
api_same = {"fixture_id": 1559000, "home": "Ipswich", "away": "Liverpool",
            "kickoff": "2026-09-04T19:00:00+00:00"}
merged_us = fxcal.merge_upcoming([api_same], us_rows)
assert [r["fixture_id"] for r in merged_us] == [1559000, "us_31201"], merged_us

filled = fxcal.write_dashboard_upcoming(NOW, _payload([]))
assert filled[0]["fixture_id"] == "us_31200"

print("calendar_test: OK")
