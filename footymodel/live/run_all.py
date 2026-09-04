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
from . import calendar as fxcal
from . import match_detail
from .client import ApiFootballClient, ApiFootballError
from .engine import (LEAGUE_API_IDS, LIVE_LOG, DEFAULT_HOURS_AHEAD, DEFAULT_HOURS_BEHIND,
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
    `all_fixtures` and render as "analysis pending" forever. Deduplicates by
    fixture_id - `all_fixtures` is built from 3 separate date-string queries,
    and a fixture near a day boundary could plausibly come back from more
    than one of them."""
    upcoming = []
    seen_ids = set()
    for fx in all_fixtures:
        if api_id_to_div.get(fx["league"]["id"]) is None:
            continue
        if pd.Timestamp(fx["fixture"]["date"]) <= now:
            continue
        fid = fx["fixture"]["id"]
        if fid in seen_ids:
            continue
        seen_ids.add(fid)
        upcoming.append({
            "fixture_id": fid,
            "home": fx["teams"]["home"]["name"],
            "away": fx["teams"]["away"]["name"],
            "kickoff": fx["fixture"]["date"],
        })
    upcoming.sort(key=lambda r: (r["kickoff"], r["home"]))
    return upcoming


def process_one_fixture(fx: dict, client: ApiFootballClient, goals: LiveWatcher,
                        props: PropsWatcher, div: str) -> tuple[dict | None, list[dict]] | None:
    """Fetch lineups+odds for one fixture and run both engines against it.

    Returns `None` if lineups aren't confirmed yet (or the lineups fetch
    itself fails) - the caller should NOT mark this fixture `seen`, since a
    later poll might still catch it once lineups are published. Returns
    `(goal_row_or_None, prop_rows)` once lineups ARE confirmed and
    processing was attempted - the caller SHOULD mark it `seen` at that
    point regardless of whether a valid prediction came out, since the
    lineup data won't change on a retry (a team-name mismatch or an
    insufficient matched-starters count isn't going to fix itself).

    Shared by run_all.py's regular poll loop and scripts/backfill_missed_fixtures.py,
    so this fetch/process/error-handling logic exists in exactly one place.
    """
    fid = fx["fixture"]["id"]
    try:
        lineups = client.lineups(fid)
    except ApiFootballError as e:
        print(f"  ! lineups fetch failed for fixture {fid}: {e}")
        return None
    if len(lineups) < 2:
        return None  # not confirmed yet — caller will retry on next poll

    print(f"  confirmed lineups: {fx['teams']['home']['name']} v "
          f"{fx['teams']['away']['name']}")

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

    prop_rows = []
    # Player-props engine is E0-only for now (see shots_engine.py docstring).
    if div == PROPS_LEAGUE:
        try:
            prop_rows = props.player_rows_for_fixture(fx, lineups, odds_resp)
        except Exception as e:
            print(f"  ! props-engine error: {e}")

    return goal_row, prop_rows


def run_once(hours_ahead: int = DEFAULT_HOURS_AHEAD,
            hours_behind: int = DEFAULT_HOURS_BEHIND) -> tuple[list[dict], list[dict]]:
    client = ApiFootballClient()
    goals = LiveWatcher(client)
    props = PropsWatcher(client)

    seen = _load_seen()
    now = pd.Timestamp.now(tz="UTC")
    api_id_to_div = {v: k for k, v in LEAGUE_API_IDS.items()}

    # Default look-ahead is today+2 days. The saved calendar can add an extra
    # date (typically yesterday) when a delayed poll still has an unseen
    # fixture inside DEFAULT_HOURS_BEHIND — without that, the 24h backward
    # window never sees fixtures whose UTC date has already rolled off.
    all_fixtures = []
    for date_str in sorted(fxcal.date_buckets_to_fetch(now)):
        try:
            all_fixtures.extend(client.fixtures_by_date(date_str))
        except ApiFootballError as e:
            print(f"! fixtures fetch failed for {date_str}: {e}")

    try:
        live_upcoming = build_upcoming_list(all_fixtures, api_id_to_div, now)
        # Calendar horizon is ~10 days; the live fetch is only ~3. Merge so
        # the dashboard keeps showing next weekend during a quiet midweek.
        upcoming = fxcal.merge_upcoming(
            live_upcoming,
            fxcal.merge_upcoming(
                fxcal.upcoming_from_calendar(now),
                fxcal.upcoming_from_understat(now),
            ),
        )
        upcoming.sort(key=lambda r: (r["kickoff"], r["home"]))
        UPCOMING_LOG.parent.mkdir(parents=True, exist_ok=True)
        UPCOMING_LOG.write_text(json.dumps(upcoming))
        try:
            from . import watchlist as wl
            wl.write_watchlist(upcoming)
        except Exception as e:
            print(f"  ! watchlist write failed (upcoming list itself is fine): {e}")
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
        if not (-hours_behind * 60 <= mins_to_ko <= hours_ahead * 60):
            continue

        result = process_one_fixture(fx, client, goals, props, div)
        if result is None:
            continue  # lineups not confirmed yet — caller will retry on next poll

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
