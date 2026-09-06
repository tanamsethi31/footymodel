"""Daily grading of past goals-engine predictions against real results.

Separate from the 20-min live poller (live_poll.yml). Works for predictions
logged by Apify, RapidAPI, SofaScore, or legacy API-Football engines.

Primary result lookup is Apify matchDetails (API-Football account suspended).
Legacy plain integer fixture ids still try API-Football when a key is set.
"""
from __future__ import annotations

import csv
import json
import os

import numpy as np
import pandas as pd

from ..data import PROCESSED_DIR
from . import apify_engine, namematch, rapidapi_engine, sofascore_engine
from .apify_client import ApifyFootballClient
from .client import ApiFootballClient, ApiFootballError
from .engine import _best_over_under_odds
from .rapidapi_client import RapidApiClient
from .sofascore_client import SofaScoreClient

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


def _spend_rapidapi_budget(budget: dict, n: int = 1) -> bool:
    """Local copy of RapidApiWatcher._spend() (rapidapi_engine.py) - same
    check-and-deduct logic, kept separate since instantiating the full
    Watcher here would also load players/build LineupModels for no reason.
    Shares the SAME rapidapi_budget.json file/BUDGET_CAP the live engine
    draws from - a closing-odds fetch here must never push total monthly
    usage over the cap."""
    if budget["calls_used"] + n > rapidapi_engine.BUDGET_CAP:
        return False
    budget["calls_used"] += n
    return True


def _fetch_closing_odds(fixture_id: str, clients: dict) -> tuple[float | None, float | None]:
    """Same-source closing-odds snapshot, fetched well after kickoff via
    whichever client originally produced this row's prediction - matching
    this project's "don't mix apples and oranges" CLV principle
    (backtest.py). (None, None) on ANY failure - a missing closing snapshot
    must never block grading the outcome itself."""
    try:
        if fixture_id.startswith("rapid_"):
            client = clients.get("rapidapi")
            budget = clients.get("rapidapi_budget")
            if client is None or budget is None:
                return None, None
            if not _spend_rapidapi_budget(budget):
                print(f"  ! rapidapi budget exhausted, skipping closing odds for {fixture_id}")
                return None, None
            event_id = int(fixture_id.removeprefix("rapid_"))
            resp = client.odds(event_id, countrycode=rapidapi_engine.ODDS_COUNTRYCODE)
            odds = rapidapi_engine._find_25_line(resp)
            return odds
        elif fixture_id.startswith("sofa_"):
            client = clients.get("sofascore")
            if client is None:
                return None, None
            event_id = int(fixture_id.removeprefix("sofa_"))
            resp = client.odds(event_id)
            return sofascore_engine._find_25_line(resp)
        elif fixture_id.startswith("apify_"):
            client = clients.get("apify")
            budget = clients.get("apify_budget")
            if client is None or budget is None:
                return None, None
            if budget["runs_used"] >= apify_engine.RUNS_CAP:
                print(f"  ! apify run cap reached, skipping closing odds for {fixture_id}")
                return None, None
            event_id = int(fixture_id.removeprefix("apify_"))
            budget["runs_used"] += 1
            rows = client.match_odds(event_id)
            return apify_engine._find_25_line(rows)
        else:
            client = clients.get("apifootball")
            if client is None:
                return None, None
            resp = client.odds(int(fixture_id))
            return _best_over_under_odds(resp)
    except Exception as e:
        # Broad on purpose - the docstring promises (None, None) on ANY
        # failure, not just the three known client errors, since a malformed
        # odds payload (bad market shape, unexpected fraction string, etc.)
        # from any of the three sources must degrade the same way.
        print(f"  ! closing-odds fetch failed for {fixture_id}: {e}")
        return None, None


def _parse_apify_scores(rows: list[dict]) -> tuple[int, int] | None:
    if not rows:
        return None
    row = rows[0]
    status = str(
        (row.get("rawStatus") or {}).get("type")
        or row.get("matchStatus")
        or ""
    ).lower()
    if status not in ("finished", "ended"):
        return None
    home = row.get("homeScore")
    away = row.get("awayScore")
    if home is None or away is None:
        return None
    return int(home), int(away)


def _lookup_finished_apify_match(
    client: ApifyFootballClient,
    budget: dict,
    match_id: int,
) -> tuple[int, int] | None:
    if budget["runs_used"] >= apify_engine.RUNS_CAP:
        print(f"  ! apify run cap reached, cannot look up match {match_id}")
        return None
    budget["runs_used"] += 1
    rows = client.run("matchDetails", matchId=match_id)
    return _parse_apify_scores(rows)


def _lookup_finished_apify_by_teams(
    row: pd.Series,
    client: ApifyFootballClient,
    budget: dict,
    cache: dict[str, list[dict]],
) -> tuple[int, int] | None:
    kickoff = pd.Timestamp(row["kickoff"])
    date_str = kickoff.strftime("%Y-%m-%d")
    if date_str not in cache:
        if budget["runs_used"] >= apify_engine.RUNS_CAP:
            cache[date_str] = []
            return None
        budget["runs_used"] += 1
        season_id = apify_engine.resolve_season_id(client, "E0")
        rows = client.league_fixtures(
            apify_engine.TOURNAMENT_IDS["E0"],
            season_id,
            span="last",
            max_pages=2,
            max_results=60,
        )
        cache[date_str] = rows

    names = []
    for r in cache[date_str]:
        names.append(r.get("homeTeamName") or "")
        names.append(r.get("awayTeamName") or "")
    home_match = namematch.best_match(row["home"], names, threshold=0.6)
    away_match = namematch.best_match(row["away"], names, threshold=0.6)
    for r in cache[date_str]:
        if (r.get("homeTeamName") == home_match and r.get("awayTeamName") == away_match):
            scores = _parse_apify_scores([r])
            if scores is not None:
                return scores
    return None


def _lookup_finished_fixture(
    row: pd.Series,
    cache: dict[str, list[dict]],
    clients: dict,
) -> tuple[int, int] | None:
    fixture_id = str(row["fixture_id"])
    apify = clients.get("apify")
    apify_budget = clients.get("apify_budget")

    if fixture_id.startswith("apify_") and apify and apify_budget is not None:
        try:
            match_id = int(fixture_id.removeprefix("apify_"))
        except ValueError:
            return None
        return _lookup_finished_apify_match(apify, apify_budget, match_id)

    if apify and apify_budget is not None:
        scores = _lookup_finished_apify_by_teams(row, apify, apify_budget, cache)
        if scores is not None:
            return scores

    apifootball = clients.get("apifootball")
    if apifootball is None:
        return None

    fx = None
    try:
        fx = apifootball.fixture_by_id(int(fixture_id))
    except ValueError:
        pass
    except ApiFootballError as e:
        print(f"  ! fixture id {fixture_id} lookup failed: {e}")

    if fx is None:
        kickoff = pd.Timestamp(row["kickoff"])
        date_str = kickoff.strftime("%Y-%m-%d")
        if date_str not in cache:
            try:
                fixtures = apifootball.fixtures_by_date(date_str)
            except ApiFootballError as e:
                print(f"  ! date {date_str} out of range or errored, skipping: {e}")
                cache[date_str] = []
                return None
            cache[date_str] = [f for f in fixtures if f["league"]["id"] == 39]

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
        return None
    home_goals = fx["goals"]["home"]
    away_goals = fx["goals"]["away"]
    if home_goals is None or away_goals is None:
        return None
    return int(home_goals), int(away_goals)


def grade_row(row: pd.Series, cache: dict[str, list[dict]], clients: dict) -> dict | None:
    """Grade one prediction row against the finished match score."""
    scores = _lookup_finished_fixture(row, cache, clients)
    if scores is None:
        return None
    home_goals, away_goals = scores
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

    closing_odds_over25 = closing_odds_under25 = bet_clv = None
    if bet_side is not None:
        closing_odds_over25, closing_odds_under25 = _fetch_closing_odds(
            str(row["fixture_id"]), clients)
        closing_bet_odds = closing_odds_over25 if bet_side == "over" else closing_odds_under25
        if closing_bet_odds:
            bet_clv = round(bet_odds / closing_bet_odds - 1, 4)

    return {
        "fixture_id": row["fixture_id"],
        "home": row["home"], "away": row["away"], "kickoff": row["kickoff"],
        "actual_home_goals": home_goals, "actual_away_goals": away_goals,
        "actual_total_goals": total_goals, "actual_over_won": actual_over_won,
        "model_p_over25": round(model_p_over25, 3), "model_correct": model_correct,
        "bet_side": bet_side, "bet_odds": bet_odds, "bet_won": bet_won,
        "realized_return": realized_return,
        "closing_odds_over25": closing_odds_over25,
        "closing_odds_under25": closing_odds_under25,
        "bet_clv": bet_clv,
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

    fixture_ids = to_grade["fixture_id"].astype(str)
    clients: dict = {}
    if os.environ.get("API_FOOTBALL_KEY"):
        try:
            clients["apifootball"] = ApiFootballClient()
        except ApiFootballError as e:
            print(f"! API-Football client unavailable ({e}); grading via Apify only")

    try:
        clients["apify"] = ApifyFootballClient()
        clients["apify_budget"] = apify_engine._load_budget()
    except Exception as e:
        print(f"! Apify client unavailable ({e})")
        if not clients:
            return
    if fixture_ids.str.startswith("rapid_").any():
        clients["rapidapi"] = RapidApiClient()
        clients["rapidapi_budget"] = rapidapi_engine._load_budget()

    sofascore_client = None
    if fixture_ids.str.startswith("sofa_").any():
        sofascore_client = SofaScoreClient()
        clients["sofascore"] = sofascore_client

    cache: dict[str, list[dict]] = {}
    graded_rows = []
    try:
        for _, row in to_grade.iterrows():
            print(f"  grading {row['home']} v {row['away']} ({row['kickoff']})")
            try:
                result = grade_row(row, cache, clients)
            except Exception as e:
                print(f"  ! grading failed unexpectedly for {row['fixture_id']}: {e}")
                continue
            if result is not None:
                graded_rows.append(result)
            else:
                print("    not gradeable yet (match not finished or lookup failed)")
    finally:
        if "rapidapi_budget" in clients:
            rapidapi_engine._save_budget(clients["rapidapi_budget"])
        if "apify_budget" in clients:
            apify_engine._save_budget(clients["apify_budget"])
        if sofascore_client is not None:
            sofascore_client.close()

    if graded_rows:
        df = pd.DataFrame(graded_rows)
        GRADED_LOG.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(GRADED_LOG, mode="a", header=not GRADED_LOG.exists(), index=False)
        print(f"Graded {len(graded_rows)} prediction(s) -> {GRADED_LOG}")
    else:
        print("No fixtures could be graded this run.")


if __name__ == "__main__":
    main()
