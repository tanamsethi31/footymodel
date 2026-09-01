"""One-off/reusable backfill: re-run the confirmed-lineup pipeline against
specific past dates that have already rolled out of run_all.py's normal
3-day forward-looking window (e.g. because a GitHub Actions cron gap meant
no poll ever ran during that date's confirmed-lineup window, and today is
now several days later). Shares the same `seen` set and output CSVs as the
regular live poll (via run_all.py's process_one_fixture), so it can never
double-log a fixture the regular poll already caught, and won't be
reprocessed by a later regular poll either.

Date-based backfill uses fixtures_by_date(), which the API-Football free
tier blocks once a date rolls out of its own rolling ~3-day window. If a
date-based backfill reports "fixtures fetch failed... Free plans do not
have access to this date", the individual fixture IDs are usually still
reachable directly (confirmed: /fixtures?id=X isn't subject to that
restriction) - pass them with --ids instead.

Usage:
    python scripts/backfill_missed_fixtures.py 2026-08-30 2026-08-31
    python scripts/backfill_missed_fixtures.py --ids 1557379 1557382
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live import match_detail
from footymodel.live.client import ApiFootballClient, ApiFootballError
from footymodel.live.engine import LEAGUE_API_IDS, LIVE_LOG, LiveWatcher, _load_seen, _save_seen
from footymodel.live.run_all import process_one_fixture
from footymodel.live.shots_engine import PROPS_LOG, PropsWatcher


def backfill(dates: list[str] = (), fixture_ids: list[int] = ()) -> tuple[list[dict], list[dict]]:
    client = ApiFootballClient()
    goals = LiveWatcher(client)
    props = PropsWatcher(client)
    seen = _load_seen()
    api_id_to_div = {v: k for k, v in LEAGUE_API_IDS.items()}

    all_fixtures = []
    for date_str in dates:
        try:
            all_fixtures.extend(client.fixtures_by_date(date_str))
        except ApiFootballError as e:
            print(f"! fixtures fetch failed for {date_str}: {e}")
    for fid in fixture_ids:
        try:
            fx = client.fixture_by_id(fid)
        except ApiFootballError as e:
            print(f"! fixture fetch failed for id {fid}: {e}")
            continue
        if fx is None:
            print(f"! fixture id {fid} not found")
            continue
        all_fixtures.append(fx)

    goal_rows, prop_rows = [], []
    for fx in all_fixtures:
        div = api_id_to_div.get(fx["league"]["id"])
        if div is None:
            continue  # not one of our confirmed-model leagues
        fid = fx["fixture"]["id"]
        if fid in seen:
            continue  # already logged by the regular poll or a prior backfill run

        result = process_one_fixture(fx, client, goals, props, div)
        if result is None:
            continue  # lineups were never confirmed for this one - nothing to recover

        goal_row, fixture_prop_rows = result
        if goal_row is not None:
            goal_rows.append(goal_row)
        prop_rows.extend(fixture_prop_rows)
        seen.add(fid)

    match_detail.extract_and_log_details(goal_rows)
    if goal_rows:
        df = pd.DataFrame(goal_rows)
        LIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(LIVE_LOG, mode="a", header=not LIVE_LOG.exists(), index=False)
        print(f"Logged {len(goal_rows)} new goals recommendation(s) -> {LIVE_LOG}")
    if prop_rows:
        df = pd.DataFrame(prop_rows)
        PROPS_LOG.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(PROPS_LOG, mode="a", header=not PROPS_LOG.exists(), index=False)
        print(f"Logged {len(prop_rows)} player-prop rows -> {PROPS_LOG}")
    if not goal_rows and not prop_rows:
        print("No new confirmed-lineup fixtures found for the given date(s).")

    _save_seen(seen)
    return goal_rows, prop_rows


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/backfill_missed_fixtures.py YYYY-MM-DD [YYYY-MM-DD ...]")
        print("   or: python scripts/backfill_missed_fixtures.py --ids FIXTURE_ID [FIXTURE_ID ...]")
        sys.exit(1)
    if sys.argv[1] == "--ids":
        backfill(fixture_ids=[int(x) for x in sys.argv[2:]])
    else:
        backfill(dates=sys.argv[1:])
