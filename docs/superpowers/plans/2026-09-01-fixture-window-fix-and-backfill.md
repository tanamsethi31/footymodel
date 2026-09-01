# Fixture Window Fix & Weekend Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the live-prediction engine from permanently losing a fixture once its kickoff has passed, and recover the 5 real Premier League matches from the Aug 30-31 weekend that were lost this way.

**Architecture:** Widen the fixture-eligibility window in both `engine.py` and `run_all.py` (the actual production entry point) to also accept recently-kicked-off fixtures, not just future ones. Extract the shared per-fixture processing logic in `run_all.py` into one function so a new backfill script can reuse it instead of duplicating it. Then actually run that backfill against the two real dates that were missed.

**Tech Stack:** Python 3.11, pandas, the existing `ApiFootballClient`/`LiveWatcher`/`PropsWatcher` classes in `footymodel/live/`.

See spec: `docs/superpowers/specs/2026-09-01-fixture-window-fix-and-backfill-design.md`

---

### Task 1: Widen `engine.py`'s own window check

**Files:**
- Modify: `footymodel/live/engine.py`

- [ ] **Step 1: Add the new constant and widen `LiveWatcher.run_once()`'s window check**

In `footymodel/live/engine.py`, find:

```python
# Lineups per API-Football docs: available 20-40 min pre-kickoff. Poll inside
# this window; a shorter default lookahead keeps requests cheap on Free tier.
DEFAULT_HOURS_AHEAD = 2
```

Replace with:

```python
# Lineups per API-Football docs: available 20-40 min pre-kickoff. Poll inside
# this window; a shorter default lookahead keeps requests cheap on Free tier.
DEFAULT_HOURS_AHEAD = 2

# Confirmed-lineup data never expires once published, but a GitHub Actions
# cron gap (observed up to ~19h between scheduled runs in practice) can push
# a fixture's kickoff into the past before any poll ever sees it. Without a
# backward allowance, that fixture is lost forever even though nothing about
# it actually changed. 24h comfortably covers same-day cron gaps plus a
# safety margin near a day boundary, at a bounded cost - no extra date-fetch
# calls, just one extra lineup-check per not-yet-seen fixture per poll.
DEFAULT_HOURS_BEHIND = 24
```

Then find, inside `LiveWatcher.run_once()`:

```python
    def run_once(self, hours_ahead: int = DEFAULT_HOURS_AHEAD) -> list[dict]:
```

Replace with:

```python
    def run_once(self, hours_ahead: int = DEFAULT_HOURS_AHEAD,
                hours_behind: int = DEFAULT_HOURS_BEHIND) -> list[dict]:
```

Then find:

```python
            kickoff = pd.Timestamp(fx["fixture"]["date"])
            mins_to_ko = (kickoff - now).total_seconds() / 60
            if not (0 <= mins_to_ko <= hours_ahead * 60):
                continue
            print(f"  checking {fx['teams']['home']['name']} v "
                  f"{fx['teams']['away']['name']} (kickoff in {mins_to_ko:.0f}min)")
```

Replace with:

```python
            kickoff = pd.Timestamp(fx["fixture"]["date"])
            mins_to_ko = (kickoff - now).total_seconds() / 60
            if not (-hours_behind * 60 <= mins_to_ko <= hours_ahead * 60):
                continue
            print(f"  checking {fx['teams']['home']['name']} v "
                  f"{fx['teams']['away']['name']} (kickoff in {mins_to_ko:.0f}min)")
```

- [ ] **Step 2: Verify the module still imports and the untouched pipeline still works**

This specific function (`LiveWatcher.run_once()`) has no dedicated automated test — it's unused in production (the cron calls `run_all.run_once()`, fixed in Task 2) and is only reachable via manual `python -m footymodel.live.engine` or `scripts/live_dryrun.py` (which calls `process_fixture()` directly, not `run_once()`, so it's unaffected by this change). Run the existing pipeline test to confirm nothing broke:

Run: `python scripts/live_dryrun.py`
Expected: ends with `ALL CHECKS PASSED — pipeline plumbing is correct end-to-end.`

- [ ] **Step 3: Commit**

```bash
git add footymodel/live/engine.py
git commit -m "fix: widen engine.py's fixture window to allow a 24h backward margin"
```

---

### Task 2: Widen `run_all.py`'s window (the real production path) and extract `process_one_fixture`

**Files:**
- Modify: `footymodel/live/run_all.py`
- Modify: `scripts/run_all_dryrun.py`

- [ ] **Step 1: Update the test first — add a past-kickoff fixture and updated expectations**

In `scripts/run_all_dryrun.py`, find:

```python
fixture = {
    "fixture": {"id": 999003,
               "date": (pd.Timestamp.now(tz="UTC") + pd.Timedelta(minutes=30)).isoformat()},
    "league": {"id": 39},  # E0
    "teams": {"home": {"id": 50, "name": home_us}, "away": {"id": 29, "name": away_us}},
}
mock_lineups = [
    {"team": {"id": 50, "name": home_us}, "startXI": [{"player": {"name": n}} for n in home_names]},
    {"team": {"id": 29, "name": away_us}, "startXI": [{"player": {"name": n}} for n in away_names]},
]
mock_odds = [{"bookmakers": [{"bets": [
    {"name": "Goals Over/Under",
     "values": [{"value": "Over 2.5", "odd": "1.9"}, {"value": "Under 2.5", "odd": "1.9"}]},
    {"name": "Home Player Shots",
     "values": [{"value": f"{home_names[0]} - 1+", "odd": "1.75"}]},
]}]}]

mock_client = MagicMock()
mock_client.fixtures_by_date.side_effect = lambda date_str: [fixture]
mock_client.lineups.return_value = mock_lineups
mock_client.odds.return_value = mock_odds

run_all.ApiFootballClient = lambda: mock_client

goal_rows, prop_rows = run_all.run_once()

print(f"fixtures_by_date calls: {mock_client.fixtures_by_date.call_count} (expect 3 — today+tomorrow+day-after)")
print(f"lineups calls: {mock_client.lineups.call_count} (expect 1 — SHARED across both engines)")
print(f"odds calls: {mock_client.odds.call_count} (expect 1 — SHARED across both engines)")
print(f"goal_rows: {len(goal_rows)} (expect 1)")
print(f"prop_rows: {len(prop_rows)} (expect 22)")

assert mock_client.fixtures_by_date.call_count == 3
assert mock_client.lineups.call_count == 1, "lineups must be fetched ONCE and shared, not once per engine"
assert mock_client.odds.call_count == 1, "odds must be fetched ONCE and shared, not once per engine"
assert len(goal_rows) == 1
assert len(prop_rows) == 22
sample_row = [r for r in prop_rows if r["player"] == home_names[0]][0]
assert sample_row["odds_shots_gt0.5"] == 1.75, "expected mocked player-shots odds to reach the props row"

upcoming = json.loads(run_all.UPCOMING_LOG.read_text())
assert upcoming and upcoming[0]["fixture_id"] == fixture["fixture"]["id"], (
    "expected the mocked fixture to actually reach upcoming_fixtures.json, not just a silent write"
)
print(f"upcoming_fixtures.json: {len(upcoming)} row(s), fixture_id={upcoming[0]['fixture_id']}")

print("\nALL CHECKS PASSED — shared fetch confirmed, no duplicate API-Football calls.")
```

Replace with:

```python
fixture = {
    "fixture": {"id": 999003,
               "date": (pd.Timestamp.now(tz="UTC") + pd.Timedelta(minutes=30)).isoformat()},
    "league": {"id": 39},  # E0
    "teams": {"home": {"id": 50, "name": home_us}, "away": {"id": 29, "name": away_us}},
}
# A fixture whose kickoff already passed (an hour ago) but still has
# confirmed lineups available - this is the exact shape of the 5 real
# matches a GitHub Actions cron gap lost over the 2026-08-30/31 weekend.
# Its lineup/odds data is identical to `fixture`'s (this test only cares
# about the window logic, not a second distinct roster).
fixture_past = {
    "fixture": {"id": 999004,
               "date": (pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=1)).isoformat()},
    "league": {"id": 39},  # E0
    "teams": {"home": {"id": 50, "name": home_us}, "away": {"id": 29, "name": away_us}},
}
mock_lineups = [
    {"team": {"id": 50, "name": home_us}, "startXI": [{"player": {"name": n}} for n in home_names]},
    {"team": {"id": 29, "name": away_us}, "startXI": [{"player": {"name": n}} for n in away_names]},
]
mock_odds = [{"bookmakers": [{"bets": [
    {"name": "Goals Over/Under",
     "values": [{"value": "Over 2.5", "odd": "1.9"}, {"value": "Under 2.5", "odd": "1.9"}]},
    {"name": "Home Player Shots",
     "values": [{"value": f"{home_names[0]} - 1+", "odd": "1.75"}]},
]}]}]

mock_client = MagicMock()
mock_client.fixtures_by_date.side_effect = lambda date_str: [fixture, fixture_past]
mock_client.lineups.return_value = mock_lineups
mock_client.odds.return_value = mock_odds

run_all.ApiFootballClient = lambda: mock_client

goal_rows, prop_rows = run_all.run_once()

print(f"fixtures_by_date calls: {mock_client.fixtures_by_date.call_count} (expect 3 — today+tomorrow+day-after)")
print(f"lineups calls: {mock_client.lineups.call_count} (expect 2 — one per unique fixture, SHARED across both engines)")
print(f"odds calls: {mock_client.odds.call_count} (expect 2 — one per unique fixture, SHARED across both engines)")
print(f"goal_rows: {len(goal_rows)} (expect 2 — both the future AND the already-kicked-off fixture)")
print(f"prop_rows: {len(prop_rows)} (expect 44 — 22 per fixture)")

assert mock_client.fixtures_by_date.call_count == 3
assert mock_client.lineups.call_count == 2, "lineups must be fetched ONCE PER FIXTURE and shared, not once per engine"
assert mock_client.odds.call_count == 2, "odds must be fetched ONCE PER FIXTURE and shared, not once per engine"
assert len(goal_rows) == 2
assert any(r["fixture_id"] == fixture_past["fixture"]["id"] for r in goal_rows), (
    "expected the already-kicked-off fixture to still be logged thanks to the widened backward window"
)
assert len(prop_rows) == 44
sample_row = [r for r in prop_rows if r["player"] == home_names[0]][0]
assert sample_row["odds_shots_gt0.5"] == 1.75, "expected mocked player-shots odds to reach the props row"

upcoming = json.loads(run_all.UPCOMING_LOG.read_text())
assert len(upcoming) == 1 and upcoming[0]["fixture_id"] == fixture["fixture"]["id"], (
    "expected only the still-upcoming fixture in upcoming_fixtures.json - the already-kicked-off "
    "one must NOT appear there even though it does get a real prediction"
)
print(f"upcoming_fixtures.json: {len(upcoming)} row(s), fixture_id={upcoming[0]['fixture_id']}")

print("\nALL CHECKS PASSED — shared fetch confirmed, no duplicate API-Football calls, "
      "past-kickoff fixture recovered.")
```

- [ ] **Step 2: Run the test and confirm it FAILS against the current (unfixed) code**

Run: `python scripts/run_all_dryrun.py`
Expected: `AssertionError` (the current code only picks up `fixture`, not `fixture_past`, so `lineups.call_count` will be 1 instead of 2, and the `goal_rows` length will be 1 instead of 2).

- [ ] **Step 3: Implement the fix in `run_all.py`**

In `footymodel/live/run_all.py`, find:

```python
from .engine import (LEAGUE_API_IDS, LIVE_LOG, DEFAULT_HOURS_AHEAD,
                     LiveWatcher, _load_seen, _save_seen)
```

Replace with:

```python
from .engine import (LEAGUE_API_IDS, LIVE_LOG, DEFAULT_HOURS_AHEAD, DEFAULT_HOURS_BEHIND,
                     LiveWatcher, _load_seen, _save_seen)
```

Then find:

```python
def run_once(hours_ahead: int = DEFAULT_HOURS_AHEAD) -> tuple[list[dict], list[dict]]:
```

Replace with:

```python
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
```

Then find the fixture-processing loop:

```python
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
```

Replace with:

```python
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
```

- [ ] **Step 4: Run the test again and confirm it PASSES**

Run: `python scripts/run_all_dryrun.py`
Expected: ends with `ALL CHECKS PASSED — shared fetch confirmed, no duplicate API-Football calls, past-kickoff fixture recovered.`

- [ ] **Step 5: Commit**

```bash
git add footymodel/live/run_all.py scripts/run_all_dryrun.py
git commit -m "fix: widen run_all.py's fixture window, extract process_one_fixture"
```

---

### Task 3: Reusable backfill script

**Files:**
- Create: `scripts/backfill_missed_fixtures.py`
- Create: `scripts/backfill_missed_fixtures_test.py`

- [ ] **Step 1: Write the script**

Create `scripts/backfill_missed_fixtures.py`:

```python
"""One-off/reusable backfill: re-run the confirmed-lineup pipeline against
specific past dates that have already rolled out of run_all.py's normal
3-day forward-looking window (e.g. because a GitHub Actions cron gap meant
no poll ever ran during that date's confirmed-lineup window, and today is
now several days later). Shares the same `seen` set and output CSVs as the
regular live poll (via run_all.py's process_one_fixture), so it can never
double-log a fixture the regular poll already caught, and won't be
reprocessed by a later regular poll either.

Usage:
    python scripts/backfill_missed_fixtures.py 2026-08-30 2026-08-31
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


def backfill(dates: list[str]) -> tuple[list[dict], list[dict]]:
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
        sys.exit(1)
    backfill(sys.argv[1:])
```

- [ ] **Step 2: Write the test**

Create `scripts/backfill_missed_fixtures_test.py`:

```python
"""Test scripts/backfill_missed_fixtures.py's backfill() against a MOCKED
API response (no network, no quota spent) - confirms it recovers a fixture
whose kickoff has already passed, using the same process_one_fixture helper
(and the same seen-set/CSV files) run_all.py's regular poll shares, and that
re-running it for an already-recovered date is a safe no-op."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for footymodel.*
sys.path.insert(0, str(Path(__file__).resolve().parent))          # scripts/, for backfill_missed_fixtures

import pandas as pd

import backfill_missed_fixtures
from footymodel.live import engine, match_detail, namematch
import footymodel.live.shots_engine as shots_engine
from footymodel.players import load_players

tmp = Path(tempfile.mkdtemp())
engine.SEEN_FIXTURES_FILE = tmp / "seen.json"
engine.LIVE_LOG = tmp / "goals.csv"
backfill_missed_fixtures.LIVE_LOG = engine.LIVE_LOG
shots_engine.PROPS_LOG = tmp / "props.csv"
backfill_missed_fixtures.PROPS_LOG = shots_engine.PROPS_LOG
match_detail.MATCH_DETAIL_LOG = tmp / "match_detail.jsonl"

players = load_players()
home_us, away_us = "Manchester City", "Everton"
home_names = list(namematch.team_roster_index(players, "E0", home_us).keys())[:11]
away_names = list(namematch.team_roster_index(players, "E0", away_us).keys())[:11]

past_fixture = {
    "fixture": {"id": 999005,
               "date": (pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=20)).isoformat()},
    "league": {"id": 39},  # E0
    "teams": {"home": {"id": 50, "name": home_us}, "away": {"id": 29, "name": away_us}},
}
mock_lineups = [
    {"team": {"id": 50, "name": home_us}, "startXI": [{"player": {"name": n}} for n in home_names]},
    {"team": {"id": 29, "name": away_us}, "startXI": [{"player": {"name": n}} for n in away_names]},
]
mock_odds = [{"bookmakers": [{"bets": [
    {"name": "Goals Over/Under",
     "values": [{"value": "Over 2.5", "odd": "1.9"}, {"value": "Under 2.5", "odd": "1.9"}]},
]}]}]

mock_client = MagicMock()
mock_client.fixtures_by_date.return_value = [past_fixture]
mock_client.lineups.return_value = mock_lineups
mock_client.odds.return_value = mock_odds

backfill_missed_fixtures.ApiFootballClient = lambda: mock_client

goal_rows, prop_rows = backfill_missed_fixtures.backfill(["2026-08-30"])

print(f"fixtures_by_date calls: {mock_client.fixtures_by_date.call_count} (expect 1 - exactly the given date)")
print(f"goal_rows: {len(goal_rows)} (expect 1)")

assert mock_client.fixtures_by_date.call_count == 1, "backfill should fetch exactly the given date(s), nothing more"
assert len(goal_rows) == 1
assert goal_rows[0]["fixture_id"] == 999005, "expected the 20-hours-in-the-past fixture to be recovered"

# Running it again for the same date must be a no-op - the fixture is now `seen`.
goal_rows2, prop_rows2 = backfill_missed_fixtures.backfill(["2026-08-30"])
assert goal_rows2 == [], "re-running backfill for an already-recovered fixture must not double-log it"

print("ALL CHECKS PASSED — backfill recovers a past-kickoff fixture and is idempotent on re-run.")
```

- [ ] **Step 3: Run the test**

Run: `python scripts/backfill_missed_fixtures_test.py`
Expected: ends with `ALL CHECKS PASSED — backfill recovers a past-kickoff fixture and is idempotent on re-run.`

- [ ] **Step 4: Commit**

```bash
git add scripts/backfill_missed_fixtures.py scripts/backfill_missed_fixtures_test.py
git commit -m "feat: add reusable backfill script for missed fixture windows"
```

---

### Task 4: Run the real backfill and verify

**Files:** none (this task runs the tools built in Tasks 1-3 against live data)

- [ ] **Step 1: Run the backfill for real**

Run: `python scripts/backfill_missed_fixtures.py 2026-08-30 2026-08-31`
Expected: prints `Logged N new goals recommendation(s) -> data/processed/live_recommendations.csv` where N is however many of the 5 real matches (Aston Villa v Arsenal, Chelsea v Brighton, Leeds v Brentford, Sunderland v Fulham, Manchester United v Ipswich) actually clear the 8/11 matched-starters threshold and team-name matching — report the real number and any per-fixture warnings honestly, don't assume all 5 make it through.

- [ ] **Step 2: Inspect the result**

Run: `tail -10 data/processed/live_recommendations.csv`
Expected: new rows with `home`/`away` matching the real fixtures from Step 1's output, `kickoff` timestamps on 2026-08-30/31.

- [ ] **Step 3: Commit the recovered data**

```bash
git add data/processed/live_recommendations.csv data/processed/live_player_props.csv \
        data/processed/match_detail.jsonl data/processed/live_seen_fixtures.json
git commit -m "data: backfill missed PL predictions from the 2026-08-30/31 weekend"
```

(Only `git add` files that actually changed — `live_player_props.csv` only changes if any of the recovered fixtures were E0, which all 5 are, so it should have new rows too.)

- [ ] **Step 4: Push**

```bash
git push origin main
```

If this is rejected because `origin/main` has new commits (e.g. the regular live-poll cron pushed in the meantime), run `git pull --rebase origin main` first, then push again — this matches the pattern already established earlier this session for reconciling with the automated cron's own commits.

- [ ] **Step 5: Trigger grading for the newly-recovered matches**

Run: `gh workflow run "Grade results" --repo tanamsethi31/footymodel`

Then poll until it completes:

```bash
until gh run list --repo tanamsethi31/footymodel --workflow="Grade results" --limit 1 --json status -q '.[0].status' | grep -q completed; do sleep 10; done
gh run list --repo tanamsethi31/footymodel --workflow="Grade results" --limit 1 --json conclusion
```

Expected: `{"conclusion":"success"}`. Then `git pull` and confirm `data/processed/graded_results.csv` gained new rows for the recovered, now-finished matches.

- [ ] **Step 6: Verify live on the dashboard**

Once Vercel redeploys (poll `gh api repos/tanamsethi31/footymodel/deployments` the same way as earlier this session), open `https://footymodel.vercel.app` and confirm: the Goals O/U tab's "Show N past predictions" disclosure includes the recovered matches in correct chronological order, and the Track Record tab shows them as graded results too.
