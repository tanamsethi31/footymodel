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
A prediction whose kickoff falls further in the past than that is
PERMANENTLY ungradeable via this method - once missed, it stays missed,
since the window only ever moves forward. Grade promptly; don't let this
job go more than ~1 day without running.

Goals-only for v1 - props grading needs per-player post-match stats,
unverified across all three live sources this project has tried.
"""
from __future__ import annotations

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
# columns), and pandas' to_csv(mode="a") never rewrites it - so older rows
# have 12 fields, newer ones have 16, and pandas.read_csv errors on the
# ragged widths unless told the full column set up front (same underlying
# issue the dashboard's TypeScript parser already works around).
_FULL_COLUMNS = [
    "logged_at", "fixture_id", "league", "kickoff", "home", "away",
    "n_home_starters_matched", "n_away_starters_matched",
    "model_p_over25", "exp_total_goals", "odds_over25", "odds_under25",
    "source", "fair_p_over25", "ev_over25", "ev_under25",
]


def _read_predictions_csv() -> pd.DataFrame:
    return pd.read_csv(PREDICTIONS_LOG, header=None, names=_FULL_COLUMNS,
                       skiprows=1, engine="python")


def _load_graded_ids() -> set:
    if not GRADED_LOG.exists():
        return set()
    return set(pd.read_csv(GRADED_LOG)["fixture_id"].astype(str))


def grade_row(row: pd.Series, cache: dict[str, list[dict]], client: ApiFootballClient) -> dict | None:
    """cache: date (YYYY-MM-DD) -> that date's E0 fixtures, populated
    lazily so multiple predictions sharing a kickoff day cost one API
    call, not one per prediction."""
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
