"""Daily grading of past goals-engine predictions against real results.

Separate from the 20-min live poller (live_poll.yml) - grading a match a
few hours late is fine, and this avoids competing for RapidAPI's scarce
100/month budget. Works regardless of which engine originally logged the
prediction (API-Football, SofaScore, or RapidAPI) - the real-world match
is the same match, so results are looked up fresh via API-Football's own
date-based fixtures endpoint and matched by date + fuzzy team name, not by
each source's own fixture_id format.

Real constraint, confirmed live (2026-08-27): the free-tier date query only
covers a ~3-day rolling window (yesterday/today/tomorrow relative to now).
For predictions logged with a plain API-Football fixture_id, grade_row()
looks the match up directly by id first - unlike fixtures_by_date(), that
isn't subject to the rolling-window restriction (confirmed live, 2026-09-01:
/fixtures?id=X still returns real data for a match several days outside the
date-query window), so those are no longer permanently ungradeable once
missed. The date+fuzzy-name fallback below only still applies to
RapidAPI/SofaScore-sourced predictions, which use their own prefixed
fixture_id formats (e.g. "rapid_5868013") that don't correspond to an
API-Football fixture id - those remain window-limited. Grade promptly
regardless; don't let this job go more than ~1 day without running.

Goals-only for v1 - props grading needs per-player post-match stats,
unverified across all three live sources this project has tried.
"""
from __future__ import annotations

import csv
import json

import numpy as np
import pandas as pd

from ..data import PROCESSED_DIR
from . import namematch
from .client import ApiFootballClient, ApiFootballError

PREDICTIONS_LOG = PROCESSED_DIR / "live_recommendations.csv"
GRADED_LOG = PROCESSED_DIR / "graded_results.csv"

# Matches older than this are outside API-Football's free-tier date-query
# window regardless of what "today" is - don't even try, just skip.
MAX_GRADE_AGE_DAYS = 4
GRADE_DELAY_HOURS = 3  # give the match time to actually finish


# live_recommendations.csv's header was written by the FIRST row ever
# appended (before source/fair_p_over25/ev_over25/ev_under25 existed as
# columns), and pandas' to_csv(mode="a") never rewrites it - so rows have a
# ragged number of trailing fields depending on which engine logged them AND
# whether odds were available at the time:
#   - engine.py never writes "source" at all -> 0 extra fields (no odds) or
#     3 (fair_p/ev_over/ev_under, all-or-nothing together)
#   - rapidapi_engine.py / sofascore_engine.py always write "source" -> 1
#     extra field (source only, no odds) or 4 (source + the same triple)
# These four lengths (0/1/3/4) never collide, so the row's actual field
# count tells us which fields are present - a fixed pd.read_csv(names=...)
# assumed every row had exactly 16 fields and silently mis-shifted any
# row that didn't (confirmed live: the first engine.py row that ever got
# real odds - Crystal Palace v Man City, 2026-08-28 - had its ev_over25
# read as ev_under25's real value, with ev_under25 itself coming back
# blank, which meant a real +7.3% EV bet was silently never placed). Same
# underlying bug already fixed on the TypeScript side, see
# dashboard/lib/data.ts's getGoalsPicks().
_BASE_COLUMNS = [
    "logged_at", "fixture_id", "league", "kickoff", "home", "away",
    "n_home_starters_matched", "n_away_starters_matched",
    "model_p_over25", "exp_total_goals", "odds_over25", "odds_under25",
]
_TRIPLE_COLUMNS = ["fair_p_over25", "ev_over25", "ev_under25"]
_NUMERIC_COLUMNS = [
    "n_home_starters_matched", "n_away_starters_matched", "model_p_over25",
    "exp_total_goals", "odds_over25", "odds_under25",
] + _TRIPLE_COLUMNS


def _num(v: str) -> float:
    return float(v) if v not in (None, "") else float("nan")


def parse_prediction_row(raw: list[str]) -> dict:
    """Map one raw CSV row (already comma-split) to its real fields by
    actual length, not by a fixed position - see the module-level comment
    for why a fixed 16-column mapping silently corrupts ragged rows."""
    row = dict(zip(_BASE_COLUMNS, raw[: len(_BASE_COLUMNS)]))
    extra = raw[len(_BASE_COLUMNS):]
    n = len(extra)
    if n in (1, 4):
        row["source"] = extra[0]
    if n in (3, 4):
        row.update(zip(_TRIPLE_COLUMNS, extra[-3:]))
    for col in _NUMERIC_COLUMNS:
        if col in row:
            row[col] = _num(row[col])
    return row


def _read_predictions_csv() -> pd.DataFrame:
    with open(PREDICTIONS_LOG, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        rows = [parse_prediction_row(raw) for raw in reader if raw]
    return pd.DataFrame(rows)


def _load_graded_ids() -> set:
    if not GRADED_LOG.exists():
        return set()
    return set(pd.read_csv(GRADED_LOG)["fixture_id"].astype(str))


def grade_row(row: pd.Series, cache: dict[str, list[dict]], client: ApiFootballClient) -> dict | None:
    """cache: date (YYYY-MM-DD) -> that date's E0 fixtures, populated
    lazily so multiple predictions sharing a kickoff day cost one API
    call, not one per prediction - only used for the date+fuzzy-name
    fallback (see below).

    Tries a direct by-id lookup first: `row["fixture_id"]` is a plain
    API-Football fixture id for anything engine.py logged (RapidAPI/
    SofaScore prefix theirs, e.g. "rapid_5868013", so `int(...)` raising
    ValueError is exactly how those fall through to the fallback below).
    Unlike fixtures_by_date(), a by-id lookup isn't subject to the free
    tier's rolling date-query window, so this is both more precise (no
    fuzzy name matching needed - we already know the exact fixture) and not
    permanently blocked once a match's date rolls out of that window."""
    fx = None
    try:
        fx = client.fixture_by_id(int(row["fixture_id"]))
    except ValueError:
        pass  # not a plain API-Football id (RapidAPI/SofaScore-prefixed) - use the fallback below
    except ApiFootballError as e:
        print(f"  ! fixture id {row['fixture_id']} lookup failed: {e}")

    if fx is None:
        kickoff = pd.Timestamp(row["kickoff"])
        date_str = kickoff.strftime("%Y-%m-%d")

        if date_str not in cache:
            try:
                fixtures = client.fixtures_by_date(date_str)
            except ApiFootballError as e:
                print(f"  ! date {date_str} out of range or errored, skipping: {e}")
                cache[date_str] = []
                return None
            cache[date_str] = [f for f in fixtures if f["league"]["id"] == 39]  # E0

        candidates = cache[date_str]
        if not candidates:
            return None

        names = [f["teams"]["home"]["name"] for f in candidates] + \
                [f["teams"]["away"]["name"] for f in candidates]
        home_match = namematch.best_match(row["home"], names, threshold=0.6)
        away_match = namematch.best_match(row["away"], names, threshold=0.6)
        fx = next((f for f in candidates
                  if f["teams"]["home"]["name"] == home_match
                  and f["teams"]["away"]["name"] == away_match), None)

    if fx is None or fx["fixture"]["status"]["short"] not in ("FT", "AET", "PEN"):
        return None  # not found, or found but not finished yet

    home_goals = fx["goals"]["home"]
    away_goals = fx["goals"]["away"]
    if home_goals is None or away_goals is None:
        return None
    total_goals = home_goals + away_goals
    actual_over_won = total_goals > 2.5

    model_p_over25 = float(row["model_p_over25"])
    model_pick_over = model_p_over25 > 0.5
    model_correct = model_pick_over == actual_over_won

    bet_side, bet_odds, bet_won, realized_return = None, None, None, None
    ev_over = row.get("ev_over25")
    ev_under = row.get("ev_under25")
    if pd.notna(ev_over) or pd.notna(ev_under):
        ev_over = ev_over if pd.notna(ev_over) else -1
        ev_under = ev_under if pd.notna(ev_under) else -1
        if ev_over > 0 or ev_under > 0:
            bet_side = "over" if ev_over >= ev_under else "under"
            bet_odds = float(row["odds_over25"] if bet_side == "over" else row["odds_under25"])
            bet_won = (bet_side == "over") == actual_over_won
            realized_return = round((bet_odds - 1) if bet_won else -1.0, 3)

    return {
        "fixture_id": row["fixture_id"],
        "home": row["home"], "away": row["away"], "kickoff": row["kickoff"],
        "actual_home_goals": home_goals, "actual_away_goals": away_goals,
        "actual_total_goals": total_goals, "actual_over_won": actual_over_won,
        "model_p_over25": round(model_p_over25, 3), "model_correct": model_correct,
        "bet_side": bet_side, "bet_odds": bet_odds, "bet_won": bet_won,
        "realized_return": realized_return,
        "graded_at": pd.Timestamp.now().isoformat(),
    }


def main() -> None:
    if not PREDICTIONS_LOG.exists():
        print("No predictions logged yet, nothing to grade.")
        return

    predictions = _read_predictions_csv()
    already_graded = _load_graded_ids()
    now = pd.Timestamp.now(tz="UTC")

    to_grade = predictions[~predictions["fixture_id"].astype(str).isin(already_graded)].copy()
    # format="mixed": the three engines log kickoff in different ISO 8601
    # variants ("...+00:00" vs "...Z" with milliseconds) - pandas silently
    # produces NaT on mixed formats without this (confirmed directly).
    to_grade["kickoff_ts"] = pd.to_datetime(to_grade["kickoff"], utc=True,
                                            format="mixed", errors="coerce")
    to_grade = to_grade[to_grade["kickoff_ts"].notna()]
    age_hours = (now - to_grade["kickoff_ts"]).dt.total_seconds() / 3600
    to_grade = to_grade[
        (age_hours >= GRADE_DELAY_HOURS) & (age_hours <= MAX_GRADE_AGE_DAYS * 24)
    ]

    if to_grade.empty:
        print("Nothing new to grade.")
        return

    client = ApiFootballClient()
    cache: dict[str, list[dict]] = {}
    graded_rows = []
    for _, row in to_grade.iterrows():
        print(f"  grading {row['home']} v {row['away']} ({row['kickoff']})")
        result = grade_row(row, cache, client)
        if result is not None:
            graded_rows.append(result)
        else:
            print("    not gradeable yet (or out of API-Football's date-query window)")

    if graded_rows:
        df = pd.DataFrame(graded_rows)
        GRADED_LOG.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(GRADED_LOG, mode="a", header=not GRADED_LOG.exists(), index=False)
        print(f"Graded {len(graded_rows)} prediction(s) -> {GRADED_LOG}")
    else:
        print("No fixtures could be graded this run.")


if __name__ == "__main__":
    main()
