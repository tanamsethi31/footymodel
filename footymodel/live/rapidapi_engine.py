"""RapidAPI-based fallback for the goals/O-U live engine, using the free
"Free API Live Football Data" listing (see rapidapi_client.py).

Two constraints shape this differently from engine.py / sofascore_engine.py:

1. Free-tier quota is 100 requests/MONTH (hard limit), not per-day. A
   budget file (rapidapi_budget.json) tracks usage and resets each
   calendar month; every call site checks remaining budget first.
2. The lineup endpoints have no confirmed/predicted flag (checked
   2026-08-27 - see .ladder/ladder.md R025). Heuristic instead of a real
   signal: only fetch lineups within LINEUP_WINDOW_MINUTES of kickoff, on
   the assumption that this close in, whatever's returned is very likely
   the real XI. Not guaranteed - a known, accepted risk given the budget
   doesn't support re-checking anyway.

To avoid spending the fixtures-scan call on every 20-min cron tick (that
alone would be ~1500/month), today's fixtures are scanned once per day and
cached locally (rapidapi_fixtures_cache.json); every cron tick just checks
the cache against the current time, no API call needed for that part.

Same LineupModel/namematch/EV logic as engine.py - only the data source,
transport, and budget/timing constraints differ. Logs to the SAME
live_recommendations.csv, tagged source="rapidapi", with its own
seen-fixtures file.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ..data import PROCESSED_DIR
from ..players import LineupModel, load_players
from ..strategy import remove_margin
from . import namematch
from .rapidapi_client import RapidApiClient, RapidApiError

# Only E0 - the one league with individually significant backtested
# evidence for the full-lineup model (RESULTS.md Phase A: E0 t=2.23 alone;
# the pooled t=3.04 across all big-5 leans on E0, the others don't clear
# significance on their own). div code -> RapidAPI leagueId, verified
# 2026-08-27 by inspecting a real matches-by-date response filtered on
# country code - the same league *name* recurs across many countries (e.g.
# "Premier League" also exists for Russia/Tanzania/etc.), so id, not name,
# is what matters here.
LEAGUE_IDS = {
    "E0": 47,   # Premier League (England)
}

LIVE_LOG = PROCESSED_DIR / "live_recommendations.csv"
SEEN_FIXTURES_FILE = PROCESSED_DIR / "rapidapi_seen_fixtures.json"
BUDGET_FILE = PROCESSED_DIR / "rapidapi_budget.json"
FIXTURES_CACHE_FILE = PROCESSED_DIR / "rapidapi_fixtures_cache.json"

BUDGET_CAP = 90  # out of 100/month - leave headroom, never chase the hard limit
LINEUP_WINDOW_MINUTES = 30  # the "probably confirmed by now" heuristic window
ODDS_COUNTRYCODE = "DE"  # verified to carry the "Total goals over/under" market;
                         # GB did not for the same fixture - untested elsewhere


def _load_seen() -> set:
    if SEEN_FIXTURES_FILE.exists():
        return set(json.loads(SEEN_FIXTURES_FILE.read_text()))
    return set()


def _save_seen(seen: set) -> None:
    SEEN_FIXTURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FIXTURES_FILE.write_text(json.dumps(sorted(seen)))


def _load_budget() -> dict:
    month = pd.Timestamp.now(tz="UTC").strftime("%Y-%m")
    if BUDGET_FILE.exists():
        b = json.loads(BUDGET_FILE.read_text())
        if b.get("month") == month:
            return b
    return {"month": month, "calls_used": 0}


def _save_budget(budget: dict) -> None:
    BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    BUDGET_FILE.write_text(json.dumps(budget))


def _load_fixtures_cache(today: str) -> list[dict] | None:
    if not FIXTURES_CACHE_FILE.exists():
        return None
    c = json.loads(FIXTURES_CACHE_FILE.read_text())
    return c.get("fixtures") if c.get("date") == today else None


def _save_fixtures_cache(today: str, fixtures: list[dict]) -> None:
    FIXTURES_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURES_CACHE_FILE.write_text(json.dumps({"date": today, "fixtures": fixtures}))


def _find_25_line(odds_resp: dict) -> tuple[float | None, float | None]:
    markets = odds_resp.get("odds", {}).get("odds", {}).get("oddsTabMarkets", [])
    for cat in markets:
        for m in cat.get("markets", []):
            if "over/under" not in (m.get("header") or "").lower():
                continue
            over = under = None
            for sel in m.get("selections", []):
                name = (sel.get("name") or "").lower()
                odd = sel.get("oddsDecimal")
                if odd is None:
                    continue
                if name == "over 2.5":
                    over = float(odd)
                elif name == "under 2.5":
                    under = float(odd)
            if over or under:
                return over, under
    return None, None


class RapidApiWatcher:
    def __init__(self, client: RapidApiClient, budget: dict):
        self.client = client
        self.budget = budget
        self.players = load_players()
        self._models: dict[str, LineupModel] = {}
        self._team_rosters: dict[tuple, dict] = {}

    def _spend(self, n: int) -> bool:
        """True and deducts if the budget allows n more calls, else False."""
        if self.budget["calls_used"] + n > BUDGET_CAP:
            return False
        self.budget["calls_used"] += n
        return True

    def _model_for(self, league: str) -> LineupModel:
        if league not in self._models:
            self._models[league] = LineupModel.fit(self.players, league, pd.Timestamp.now())
        return self._models[league]

    def _roster_for(self, league: str, team_us: str) -> dict:
        key = (league, team_us)
        if key not in self._team_rosters:
            self._team_rosters[key] = namematch.team_roster_index(self.players, league, team_us)
        return self._team_rosters[key]

    def map_lineup_to_ids(self, league: str, team_us: str, player_names: list[str]) -> list:
        roster = self._roster_for(league, team_us)
        ids, unmatched = [], []
        for name in player_names:
            pid = namematch.match_player(name, roster)
            if pid is not None:
                ids.append(pid)
            else:
                unmatched.append(name)
        if unmatched:
            print(f"    ! unmatched players for {team_us}: {unmatched}")
        return ids

    def process_fixture(self, league: str, fx: dict) -> dict | None:
        event_id = fx["id"]
        home_api, away_api = fx["home"]["name"], fx["away"]["name"]

        if not self._spend(2):
            print(f"  ! budget exhausted ({self.budget['calls_used']}/{BUDGET_CAP}), skipping remaining fixtures")
            return None
        try:
            home_lineup = self.client.home_lineup(event_id)
            away_lineup = self.client.away_lineup(event_id)
        except RapidApiError as e:
            print(f"  ! lineup fetch failed: {e}")
            return None
        home_starters = [p["name"] for p in home_lineup.get("starters", [])]
        away_starters = [p["name"] for p in away_lineup.get("starters", [])]
        if len(home_starters) < 8 or len(away_starters) < 8:
            return None  # not populated yet (too early, even within the window) or a data gap

        team_names = namematch.team_name_index(self.players, league)
        home_us = namematch.match_team(home_api, team_names)
        away_us = namematch.match_team(away_api, team_names)
        if not home_us or not away_us:
            print(f"  ! team-name match failed: {home_api} / {away_api}")
            return None

        home_ids = self.map_lineup_to_ids(league, home_us, home_starters)
        away_ids = self.map_lineup_to_ids(league, away_us, away_starters)
        if len(home_ids) < 8 or len(away_ids) < 8:
            print(f"  ! too few matched starters ({len(home_ids)}/{len(away_ids)}) "
                  f"for {home_api} v {away_api}, skipping")
            return None

        model = self._model_for(league)
        pred = model.predict(home_ids, away_ids, home_us, away_us)

        over_odds = under_odds = None
        if self._spend(1):
            try:
                odds_resp = self.client.odds(event_id, countrycode=ODDS_COUNTRYCODE)
                over_odds, under_odds = _find_25_line(odds_resp)
            except RapidApiError as e:
                print(f"  ! odds fetch failed: {e}")

        row = {
            "logged_at": pd.Timestamp.now().isoformat(),
            "fixture_id": f"rapid_{event_id}", "league": league,
            "kickoff": fx["kickoff_iso"], "home": home_api, "away": away_api,
            "n_home_starters_matched": len(home_ids), "n_away_starters_matched": len(away_ids),
            "model_p_over25": round(pred["p_over25_blend"], 3),
            "exp_total_goals": round(pred["exp_blend"], 2),
            "odds_over25": over_odds, "odds_under25": under_odds,
            "source": "rapidapi",
        }
        if over_odds and under_odds:
            fair = remove_margin(np.array([over_odds, under_odds]))
            row["fair_p_over25"] = round(float(fair[0]), 3)
            row["ev_over25"] = round(pred["p_over25_blend"] * over_odds - 1.0, 3)
            row["ev_under25"] = round((1 - pred["p_over25_blend"]) * under_odds - 1.0, 3)
        return row

    def run_once(self) -> list[dict]:
        seen = _load_seen()
        now = pd.Timestamp.now(tz="UTC")
        today = now.strftime("%Y-%m-%d")

        fixtures = _load_fixtures_cache(today)
        if fixtures is None:
            if self.budget["calls_used"] >= BUDGET_CAP:
                print("! monthly budget exhausted, cannot even scan fixtures")
                return []
            self.budget["calls_used"] += 1
            try:
                leagues = self.client.matches_by_date(now.strftime("%Y%m%d"))
            except RapidApiError as e:
                print(f"! fixtures scan failed: {e}")
                _save_budget(self.budget)
                return []
            fixtures = []
            id_to_div = {v: k for k, v in LEAGUE_IDS.items()}
            for lg in leagues:
                div = id_to_div.get(lg.get("id"))
                if div is None:
                    continue
                for m in lg.get("matches", []):
                    fixtures.append({
                        "id": m["id"], "div": div,
                        "home": m["home"], "away": m["away"],
                        "kickoff_iso": m["status"]["utcTime"],
                        "timeTS": m["timeTS"],
                    })
            _save_fixtures_cache(today, fixtures)
            print(f"  scanned {len(fixtures)} fixtures across our 5 leagues for {today}")

        new_rows = []
        for fx in fixtures:
            eid = fx["id"]
            if eid in seen:
                continue
            kickoff = pd.Timestamp(fx["timeTS"], unit="ms", tz="UTC")
            mins_to_ko = (kickoff - now).total_seconds() / 60
            if not (0 <= mins_to_ko <= LINEUP_WINDOW_MINUTES):
                continue
            if self.budget["calls_used"] >= BUDGET_CAP:
                break
            print(f"  checking {fx['home']['name']} v {fx['away']['name']} "
                  f"(kickoff in {mins_to_ko:.0f}min)")
            try:
                row = self.process_fixture(fx["div"], fx)
            except Exception as e:
                print(f"  ! error processing event {eid}: {e}")
                continue
            if row is not None:
                new_rows.append(row)
                seen.add(eid)
                _save_seen(seen)  # persist progress fixture-by-fixture, not just at the end
                _save_budget(self.budget)

        if new_rows:
            df = pd.DataFrame(new_rows)
            LIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(LIVE_LOG, mode="a", header=not LIVE_LOG.exists(), index=False)
            print(f"Logged {len(new_rows)} new recommendation(s) -> {LIVE_LOG}")
        else:
            print("No new confirmed-lineup fixtures this poll (RapidAPI).")
        print(f"  budget used this month: {self.budget['calls_used']}/{BUDGET_CAP}")
        _save_seen(seen)
        _save_budget(self.budget)
        return new_rows


if __name__ == "__main__":
    import traceback

    print("!" * 72)
    print("PAPER-TRADE / PREDICTION MODE (RapidAPI source, heuristic-confirmed). "
          "No bets placed, no money at risk.")
    print("!" * 72)
    try:
        client = RapidApiClient()
        budget = _load_budget()
        RapidApiWatcher(client, budget).run_once()
    except Exception:
        print("!" * 72)
        print("CRON RUN FAILED - nothing was logged this poll. Traceback:")
        print("!" * 72)
        traceback.print_exc()
        raise
