"""Single cron entry point driving BOTH the goals/O-U engine and the player
shots/SOT engine off ONE shared fixtures + lineups + odds fetch per poll.

Why this exists instead of two separate cron jobs: each watcher independently
fetching fixtures-by-date, lineups-per-fixture, and now odds-per-fixture
would roughly double API-Football usage for identical data (the free tier's
~78 baseline requests/day from `engine.py`'s cron comment would become ~156
just for fixture lookups, before any lineup/odds calls - already over the
100/day free-tier quota). Fetching once and handing the same lineups/odds to
both watchers keeps the request count exactly where it was with one engine.

PAPER-TRADE / PREDICTION ONLY for both - no staking. Player-prop EV (Phase I)
is naive (model_prob * odd - 1), not margin-adjusted - see shots_engine.py
docstring for why.
"""
from __future__ import annotations

import json

import pandas as pd

from ..data import PROCESSED_DIR
from . import match_detail
from .client import ApiFootballClient, ApiFootballError
from .engine import (LEAGUE_API_IDS, LIVE_LOG, DEFAULT_HOURS_AHEAD,
                     LiveWatcher, _load_seen, _save_seen)
from .shots_engine import LEAGUE as PROPS_LEAGUE
from .shots_engine import PROPS_LOG, PropsWatcher

UPCOMING_LOG = PROCESSED_DIR / "upcoming_fixtures.json"


def build_upcoming_list(all_fixtures: list[dict], api_id_to_div: dict[int, str],
                        now: pd.Timestamp) -> list[dict]:
    """Shape every tracked-league fixture that hasn't kicked off yet into the
    small preview record the dashboard shows for matches without a
    confirmed-lineup prediction yet. Doesn't check confirmation status - the
    dashboard does that itself by cross-referencing fixture_id against what
    it already has. Does exclude fixtures whose kickoff has already passed -
    without that, a fixture that never got a confirmed lineup (so never
    became a real prediction, and never entered `seen`) would sit in
    `all_fixtures` and render as "analysis pending" forever."""
    upcoming = []
    for fx in all_fixtures:
        if api_id_to_div.get(fx["league"]["id"]) is None:
            continue
        if pd.Timestamp(fx["fixture"]["date"]) <= now:
            continue
        upcoming.append({
            "fixture_id": fx["fixture"]["id"],
            "home": fx["teams"]["home"]["name"],
            "away": fx["teams"]["away"]["name"],
            "kickoff": fx["fixture"]["date"],
        })
    return upcoming


def run_once(hours_ahead: int = DEFAULT_HOURS_AHEAD) -> tuple[list[dict], list[dict]]:
    client = ApiFootballClient()
    goals = LiveWatcher(client)
    props = PropsWatcher(client)

    seen = _load_seen()
    now = pd.Timestamp.now(tz="UTC")
    api_id_to_div = {v: k for k, v in LEAGUE_API_IDS.items()}

    all_fixtures = []
    for date_str in {now.strftime("%Y-%m-%d"),
                     (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                     (now + pd.Timedelta(days=2)).strftime("%Y-%m-%d")}:
        try:
            all_fixtures.extend(client.fixtures_by_date(date_str))
        except ApiFootballError as e:
            print(f"! fixtures fetch failed for {date_str}: {e}")

    try:
        upcoming = build_upcoming_list(all_fixtures, api_id_to_div, now)
        UPCOMING_LOG.parent.mkdir(parents=True, exist_ok=True)
        UPCOMING_LOG.write_text(json.dumps(upcoming))
    except Exception as e:
        print(f"  ! failed to write upcoming_fixtures.json (predictions themselves unaffected): {e}")

    goal_rows, prop_rows = [], []
    for fx in all_fixtures:
        div = api_id_to_div.get(fx["league"]["id"])
        if div is None:
            continue  # not one of our confirmed-model leagues
        fid = fx["fixture"]["id"]
        if fid in seen:
            continue
        kickoff = pd.Timestamp(fx["fixture"]["date"])
        mins_to_ko = (kickoff - now).total_seconds() / 60
        if not (0 <= mins_to_ko <= hours_ahead * 60):
            continue

        try:
            lineups = client.lineups(fid)
        except ApiFootballError as e:
            print(f"  ! lineups fetch failed for fixture {fid}: {e}")
            continue
        if len(lineups) < 2:
            continue  # not confirmed yet — caller will retry on next poll

        print(f"  confirmed lineups: {fx['teams']['home']['name']} v "
              f"{fx['teams']['away']['name']} (kickoff in {mins_to_ko:.0f}min)")

        try:
            odds_resp = client.odds(fid)
        except ApiFootballError as e:
            print(f"  ! odds fetch failed for fixture {fid}: {e}")
            odds_resp = []

        try:
            goal_row = goals.process_fixture(div, fx, lineups, odds_resp)
        except Exception as e:
            print(f"  ! goals-engine error: {e}")
            goal_row = None
        if goal_row is not None:
            goal_rows.append(goal_row)

        # Player-props engine is E0-only for now (see shots_engine.py docstring).
        if div == PROPS_LEAGUE:
            try:
                prop_rows.extend(props.player_rows_for_fixture(fx, lineups, odds_resp))
            except Exception as e:
                print(f"  ! props-engine error: {e}")

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
        print("No new confirmed-lineup fixtures this poll.")

    _save_seen(seen)
    return goal_rows, prop_rows


if __name__ == "__main__":
    import traceback

    print("!" * 72)
    print("PAPER-TRADE / PREDICTION MODE. No bets placed, no money at risk.")
    print("!" * 72)
    try:
        run_once()
    except Exception:
        # Cron output only goes to a log file nobody watches live - make a
        # crash impossible to miss (grep-able marker) rather than a bare
        # traceback indistinguishable from a normal quiet poll.
        print("!" * 72)
        print("CRON RUN FAILED - nothing was logged this poll. Traceback:")
        print("!" * 72)
        traceback.print_exc()
        raise
