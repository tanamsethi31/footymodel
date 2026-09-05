"""Apify-based fallback for the goals O/U live engine.

Uses sian.agency/football-api-scraper on Apify — SofaScore-shaped data via
Apify's infrastructure when direct sofascore_engine.py Playwright scraping
is blocked. Shares the same LineupModel / EV math as engine.py; logs to the
same live_recommendations.csv with source="apify" and fixture ids prefixed
apify_{matchId}.

Budget: pay-per-run Actor (~$0.05 start + per-row). A monthly run cap in
apify_budget.json prevents surprise bills (same pattern as rapidapi_engine).
"""
from __future__ import annotations

import json
from fractions import Fraction

import numpy as np
import pandas as pd

from ..data import PROCESSED_DIR
from ..players import LineupModel, load_players
from ..strategy import remove_margin
from . import match_detail, namematch
from .apify_client import ApifyFootballClient, ApifyError

# E0 only — same rationale as sofascore_engine / rapidapi_engine.
TOURNAMENT_IDS = {
    "E0": 17,  # Premier League (SofaScore unique tournament id)
}
# Premier League 2025/26 — refresh via leagueSeasons if this goes stale.
SEASON_IDS = {
    "E0": 76986,
}

LIVE_LOG = PROCESSED_DIR / "live_recommendations.csv"
SEEN_FIXTURES_FILE = PROCESSED_DIR / "apify_seen_fixtures.json"
BUDGET_FILE = PROCESSED_DIR / "apify_budget.json"
FIXTURES_CACHE_FILE = PROCESSED_DIR / "apify_fixtures_cache.json"

RUNS_CAP = 60  # Actor starts/month — leave headroom on pay-per-event pricing
DEFAULT_HOURS_AHEAD = 2
# Allow a short post-kickoff recovery window when the poll was delayed past KO
# but lineups are still fetchable.
LINEUP_LOOKBACK_MINUTES = 180


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
    return {"month": month, "runs_used": 0}


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


def _frac_to_decimal(fractional: str) -> float:
    return float(Fraction(fractional)) + 1.0


def _find_25_line(markets: list[dict]) -> tuple[float | None, float | None]:
    """Pick the main match-goals O/U 2.5 line from Apify odds rows.

    The Actor returns multiple "Match goals" markets without an explicit
    handicap label. Prefer the most balanced Over/Under pair in a sensible
    band (typical main line); fall back to the third row when sorted by
    ascending Over odds (0.5, 1.5, 2.5, ...).
    """
    candidates: list[tuple[float, float]] = []
    for m in markets:
        group = (m.get("marketGroup") or m.get("marketName") or "").lower()
        if group != "match goals":
            continue
        over = under = None
        for c in m.get("oddsChoices", []):
            outcome = (c.get("outcome") or "").lower()
            frac = c.get("fractionalValue")
            if not frac:
                continue
            val = _frac_to_decimal(str(frac))
            if outcome == "over":
                over = val
            elif outcome == "under":
                under = val
        if over and under:
            candidates.append((over, under))
    if not candidates:
        return None, None

    def balance_score(pair: tuple[float, float]) -> float:
        o, u = pair
        if o < 1.35 or u < 1.35 or o > 4.0 or u > 4.0:
            return float("inf")
        return abs(o - u)

    best = min(candidates, key=balance_score)
    if best[0] != float("inf"):
        return best
    candidates.sort(key=lambda x: x[0])
    if len(candidates) >= 3:
        return candidates[2]
    return None, None


def _parse_lineups(rows: list[dict]) -> dict:
    """Collapse per-player lineup rows into home/away starter lists."""
    if not rows:
        return {"confirmed": False, "home": [], "away": []}
    confirmed = any(r.get("lineupConfirmed") for r in rows)
    home, away = [], []
    for r in rows:
        if r.get("isSubstitute"):
            continue
        name = r.get("playerName")
        if not name:
            continue
        side = r.get("lineupSide")
        if side == "home":
            home.append(str(name))
        elif side == "away":
            away.append(str(name))
    return {"confirmed": confirmed, "home": home, "away": away}


def _is_upcoming(row: dict, now: pd.Timestamp) -> bool:
    ts = row.get("startTimestamp")
    if ts is not None and int(ts) <= int(now.timestamp()):
        return False
    status = str(row.get("matchStatus") or "").lower()
    if any(x in status for x in ("end", "finish", "cancel", "postpon", "abandon")):
        return False
    raw = row.get("rawStatus")
    if isinstance(raw, dict):
        t = str(raw.get("type") or "").lower()
        if t in ("finished", "canceled", "cancelled", "postponed", "abandoned"):
            return False
    return True


class ApifyWatcher:
    def __init__(self, client: ApifyFootballClient, budget: dict):
        self.client = client
        self.budget = budget
        self.players = load_players()
        self._models: dict[str, LineupModel] = {}
        self._team_rosters: dict[tuple, dict] = {}

    def _spend(self) -> bool:
        if self.budget["runs_used"] >= RUNS_CAP:
            return False
        self.budget["runs_used"] += 1
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
        match_id = int(fx["matchId"])
        home_api = str(fx["homeTeamName"])
        away_api = str(fx["awayTeamName"])

        if not self._spend():
            print(f"  ! Apify monthly run cap reached ({RUNS_CAP}), skipping lineups")
            return None
        try:
            lineup_rows = self.client.match_lineups(match_id)
        except ApifyError as e:
            print(f"  ! lineup fetch failed: {e}")
            return None

        lineups = _parse_lineups(lineup_rows)
        if not lineups["confirmed"]:
            return None
        if len(lineups["home"]) < 8 or len(lineups["away"]) < 8:
            return None

        team_names = namematch.team_name_index(self.players, league)
        home_us = namematch.match_team(home_api, team_names)
        away_us = namematch.match_team(away_api, team_names)
        if not home_us or not away_us:
            print(f"  ! team-name match failed: {home_api} / {away_api}")
            return None

        home_ids = self.map_lineup_to_ids(league, home_us, lineups["home"])
        away_ids = self.map_lineup_to_ids(league, away_us, lineups["away"])
        if len(home_ids) < 8 or len(away_ids) < 8:
            print(f"  ! too few matched starters ({len(home_ids)}/{len(away_ids)}) "
                  f"for {home_api} v {away_api}, skipping")
            return None

        model = self._model_for(league)
        pred = model.predict(home_ids, away_ids, home_us, away_us)

        over_odds = under_odds = None
        if self._spend():
            try:
                odds_rows = self.client.match_odds(match_id)
                over_odds, under_odds = _find_25_line(odds_rows)
            except ApifyError as e:
                print(f"  ! odds fetch failed: {e}")

        kickoff = pd.Timestamp(int(fx["startTimestamp"]), unit="s", tz="UTC")
        row = {
            "logged_at": pd.Timestamp.now().isoformat(),
            "fixture_id": f"apify_{match_id}",
            "league": league,
            "kickoff": kickoff.isoformat(),
            "home": home_api,
            "away": away_api,
            "n_home_starters_matched": len(home_ids),
            "n_away_starters_matched": len(away_ids),
            "model_p_over25": round(pred["p_over25_blend"], 3),
            "exp_total_goals": round(pred["exp_blend"], 2),
            "odds_over25": over_odds,
            "odds_under25": under_odds,
            "source": "apify",
        }
        if over_odds and under_odds:
            fair = remove_margin(np.array([over_odds, under_odds]))
            row["fair_p_over25"] = round(float(fair[0]), 3)
            row["ev_over25"] = round(pred["p_over25_blend"] * over_odds - 1.0, 3)
            row["ev_under25"] = round((1 - pred["p_over25_blend"]) * under_odds - 1.0, 3)
        row["_detail"] = match_detail.make_detail(
            row["fixture_id"], lineups["home"], lineups["away"], pred)
        return row

    def run_once(self, hours_ahead: int = DEFAULT_HOURS_AHEAD) -> list[dict]:
        seen = _load_seen()
        now = pd.Timestamp.now(tz="UTC")
        today = now.strftime("%Y-%m-%d")

        fixtures = _load_fixtures_cache(today)
        if fixtures is None:
            if not self._spend():
                print("! Apify monthly run cap exhausted, cannot scan fixtures")
                return []
            try:
                rows = self.client.league_fixtures(
                    TOURNAMENT_IDS["E0"], SEASON_IDS["E0"], span="next"
                )
            except ApifyError as e:
                print(f"! fixtures scan failed: {e}")
                _save_budget(self.budget)
                return []
            fixtures = []
            for r in rows:
                if not _is_upcoming(r, now):
                    continue
                fixtures.append({
                    "matchId": r["matchId"],
                    "homeTeamName": r.get("homeTeamName") or r.get("homeTeam", {}).get("name"),
                    "awayTeamName": r.get("awayTeamName") or r.get("awayTeam", {}).get("name"),
                    "startTimestamp": r["startTimestamp"],
                })
            _save_fixtures_cache(today, fixtures)
            print(f"  cached {len(fixtures)} upcoming E0 fixtures for {today}")

        new_rows = []
        for fx in fixtures:
            mid = int(fx["matchId"])
            if mid in seen:
                continue
            kickoff = pd.Timestamp(int(fx["startTimestamp"]), unit="s", tz="UTC")
            mins_to_ko = (kickoff - now).total_seconds() / 60
            if not (-LINEUP_LOOKBACK_MINUTES <= mins_to_ko <= hours_ahead * 60):
                continue
            if self.budget["runs_used"] >= RUNS_CAP:
                break
            print(f"  checking {fx['homeTeamName']} v {fx['awayTeamName']} "
                  f"(kickoff in {mins_to_ko:.0f}min)")
            try:
                row = self.process_fixture("E0", fx)
            except Exception as e:
                print(f"  ! error processing match {mid}: {e}")
                continue
            if row is not None:
                new_rows.append(row)
                seen.add(mid)
                _save_seen(seen)
                _save_budget(self.budget)

        match_detail.extract_and_log_details(new_rows)
        if new_rows:
            df = pd.DataFrame(new_rows)
            LIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(LIVE_LOG, mode="a", header=not LIVE_LOG.exists(), index=False)
            print(f"Logged {len(new_rows)} new recommendation(s) -> {LIVE_LOG}")
        else:
            print("No new confirmed-lineup fixtures this poll (Apify).")
        print(f"  Apify runs used this month: {self.budget['runs_used']}/{RUNS_CAP}")
        _save_seen(seen)
        _save_budget(self.budget)
        return new_rows


if __name__ == "__main__":
    import traceback

    print("!" * 72)
    print("PAPER-TRADE / PREDICTION MODE (Apify football-api-scraper). "
          "No bets placed, no money at risk.")
    print("!" * 72)
    try:
        client = ApifyFootballClient()
        budget = _load_budget()
        ApifyWatcher(client, budget).run_once()
    except Exception:
        print("!" * 72)
        print("CRON RUN FAILED - nothing was logged this poll. Traceback:")
        print("!" * 72)
        traceback.print_exc()
        raise
