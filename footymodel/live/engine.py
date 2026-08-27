"""Phase B orchestrator: watch fixtures, detect confirmed lineups, run the
CONFIRMED full-lineup model (RESULTS.md, pooled t=3.04), compare to live O/U
odds, and log a timestamped recommendation. PAPER-TRADE / DETECTION ONLY —
no staking, no order placement.

API-Football league IDs below are the standard/documented ones for these
competitions but are NOT yet verified against a live key in this environment
(Cloudflare + policy blocks prevented browsing api-football.com's live league
list end-to-end). Before relying on this, run `python -m footymodel.live.engine
--verify-leagues` once you have a key — it prints what each ID actually
resolves to so you can catch any mismatch immediately.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .. import config as fm_config
from ..data import PROCESSED_DIR
from ..players import LineupModel, load_players
from ..strategy import remove_margin
from . import namematch
from .client import ApiFootballClient, ApiFootballError

# Only leagues with INDIVIDUALLY significant backtested evidence (not just
# pooled) for the full-lineup model - see RESULTS.md's Phase A per-league
# t-stats: E0 t=2.23 (significant alone), the pooled t=3.04 across all
# big-5 relies on E0 carrying most of the weight (I1 1.97 borderline, SP1
# 1.36 / D1 1.32 / F1 0.72 not significant individually). div code ->
# API-Football league id.
LEAGUE_API_IDS = {
    "E0": 39,    # Premier League
}

LIVE_LOG = PROCESSED_DIR / "live_recommendations.csv"
SEEN_FIXTURES_FILE = PROCESSED_DIR / "live_seen_fixtures.json"

# Lineups per API-Football docs: available 20-40 min pre-kickoff. Poll inside
# this window; a shorter default lookahead keeps requests cheap on Free tier.
DEFAULT_HOURS_AHEAD = 2


def _load_seen() -> set:
    if SEEN_FIXTURES_FILE.exists():
        return set(json.loads(SEEN_FIXTURES_FILE.read_text()))
    return set()


def _save_seen(seen: set) -> None:
    SEEN_FIXTURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FIXTURES_FILE.write_text(json.dumps(sorted(seen)))


def _best_over_under_odds(odds_response: list[dict]) -> tuple[float | None, float | None]:
    """Best (max) Over 2.5 / Under 2.5 odds across all bookmakers in the
    response. None if the market isn't present."""
    best_over, best_under = None, None
    for entry in odds_response:
        for bm in entry.get("bookmakers", []):
            for bet in bm.get("bets", []):
                if bet.get("name") != "Goals Over/Under":
                    continue
                for v in bet.get("values", []):
                    val = str(v.get("value", ""))
                    odd = float(v.get("odd", 0) or 0)
                    if val == "Over 2.5" and (best_over is None or odd > best_over):
                        best_over = odd
                    elif val == "Under 2.5" and (best_under is None or odd > best_under):
                        best_under = odd
    return best_over, best_under


class LiveWatcher:
    def __init__(self, client: ApiFootballClient | None = None):
        self.client = client or ApiFootballClient()
        self.players = load_players()
        self._models: dict[str, LineupModel] = {}
        self._team_rosters: dict[tuple, dict] = {}

    def _model_for(self, league: str) -> LineupModel:
        if league not in self._models:
            self._models[league] = LineupModel.fit(
                self.players, league, pd.Timestamp.now())
        return self._models[league]

    def _roster_for(self, league: str, team_us: str) -> dict:
        key = (league, team_us)
        if key not in self._team_rosters:
            self._team_rosters[key] = namematch.team_roster_index(
                self.players, league, team_us)
        return self._team_rosters[key]

    def map_lineup_to_ids(self, league: str, team_us: str, api_player_names: list[str]) -> list:
        """Note: player_id values are Understat's native string ids (e.g. '1040'),
        not ints — don't filter on type, the unmatched/matched split below already
        guarantees every entry in `ids` is a real match."""
        roster = self._roster_for(league, team_us)
        ids, unmatched = [], []
        for name in api_player_names:
            pid = namematch.match_player(name, roster)
            if pid is not None:
                ids.append(pid)
            else:
                unmatched.append(name)
        if unmatched:
            print(f"    ! unmatched players for {team_us}: {unmatched}")
        return ids

    def process_fixture(self, league: str, fixture: dict, lineups: list[dict],
                        odds_resp: list[dict] | None = None) -> dict | None:
        """`lineups` (and, if given, `odds_resp`) are fetched by the caller
        (run_all.py shares one fetch across the goals and player-props
        watchers, so running both doesn't double API-Football usage) —
        empty/short lineups list means not confirmed yet. `odds_resp=None`
        fetches it here instead, for standalone use."""
        fx = fixture["fixture"]
        teams = fixture["teams"]
        fixture_id = fx["id"]

        if len(lineups) < 2:
            return None  # not confirmed yet — caller will retry on next poll

        team_names = namematch.team_name_index(self.players, league)
        home_api, away_api = teams["home"]["name"], teams["away"]["name"]
        home_us = namematch.match_team(home_api, team_names)
        away_us = namematch.match_team(away_api, team_names)
        if not home_us or not away_us:
            print(f"  ! team-name match failed: {home_api} / {away_api}")
            return None

        # Lineups + fixture come from the SAME API, so match by team id (exact),
        # not fuzzy string matching.
        by_team_id = {l["team"]["id"]: l for l in lineups}
        home_l = by_team_id.get(teams["home"]["id"])
        away_l = by_team_id.get(teams["away"]["id"])
        if home_l is None or away_l is None:
            print(f"  ! lineup/team-id mismatch for {home_api} v {away_api}")
            return None

        home_names = [p["player"]["name"] for p in home_l.get("startXI", [])]
        away_names = [p["player"]["name"] for p in away_l.get("startXI", [])]
        home_ids = self.map_lineup_to_ids(league, home_us, home_names)
        away_ids = self.map_lineup_to_ids(league, away_us, away_names)
        if len(home_ids) < 8 or len(away_ids) < 8:  # too many unmatched to trust
            print(f"  ! too few matched starters ({len(home_ids)}/{len(away_ids)}) "
                  f"for {home_api} v {away_api}, skipping")
            return None

        model = self._model_for(league)
        pred = model.predict(home_ids, away_ids, home_us, away_us)

        if odds_resp is None:
            try:
                odds_resp = self.client.odds(fixture_id)
            except ApiFootballError as e:
                print(f"  ! odds fetch failed: {e}")
                odds_resp = []
        over_odds, under_odds = _best_over_under_odds(odds_resp)

        row = {
            "logged_at": pd.Timestamp.now().isoformat(),
            "fixture_id": fixture_id, "league": league,
            "kickoff": fx["date"], "home": home_api, "away": away_api,
            "n_home_starters_matched": len(home_ids), "n_away_starters_matched": len(away_ids),
            "model_p_over25": round(pred["p_over25_blend"], 3),
            "exp_total_goals": round(pred["exp_blend"], 2),
            "odds_over25": over_odds, "odds_under25": under_odds,
        }
        if over_odds and under_odds:
            fair = remove_margin(np.array([over_odds, under_odds]))
            row["fair_p_over25"] = round(float(fair[0]), 3)
            row["ev_over25"] = round(pred["p_over25_blend"] * over_odds - 1.0, 3)
            row["ev_under25"] = round((1 - pred["p_over25_blend"]) * under_odds - 1.0, 3)
        return row

    def run_once(self, hours_ahead: int = DEFAULT_HOURS_AHEAD) -> list[dict]:
        """Query fixtures by DATE ONLY (no league/season filter) and filter
        client-side by league id. The API-Football Free tier blocks the
        league+season combo for the current season/date but date-only queries
        work fine — confirmed against a live key on 2026-07-28."""
        seen = _load_seen()
        new_rows = []
        now = pd.Timestamp.now(tz="UTC")
        api_id_to_div = {v: k for k, v in LEAGUE_API_IDS.items()}

        # Cover a day boundary: fetch today's and tomorrow's date buckets.
        all_fixtures = []
        for date_str in {now.strftime("%Y-%m-%d"),
                         (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d")}:
            try:
                all_fixtures.extend(self.client.fixtures_by_date(date_str))
            except ApiFootballError as e:
                print(f"! fixtures fetch failed for {date_str}: {e}")

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
            print(f"  checking {fx['teams']['home']['name']} v "
                  f"{fx['teams']['away']['name']} (kickoff in {mins_to_ko:.0f}min)")
            try:
                lineups = self.client.lineups(fid)
                row = self.process_fixture(div, fx, lineups)
            except Exception as e:
                print(f"  ! error processing fixture {fid}: {e}")
                continue
            if row is not None:
                new_rows.append(row)
                seen.add(fid)

        if new_rows:
            df = pd.DataFrame(new_rows)
            LIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(LIVE_LOG, mode="a", header=not LIVE_LOG.exists(), index=False)
            print(f"Logged {len(new_rows)} new recommendation(s) -> {LIVE_LOG}")
        else:
            print("No new confirmed-lineup fixtures this poll.")
        _save_seen(seen)
        return new_rows


def verify_leagues():
    """Print what each hardcoded league ID actually resolves to — run this
    once with a real key before trusting LEAGUE_API_IDS.

    Uses the `leagues?id=` lookup, not fixtures?league=&season= — the latter is
    blocked on the API-Football Free tier for the current season (confirmed
    2026-07-26: "Free plans do not have access to this season, try from 2022 to
    2024"). Live fixture fetching in run_once() instead queries by DATE ONLY
    (works on Free tier) and filters by league id client-side."""
    client = ApiFootballClient()
    for div, api_id in LEAGUE_API_IDS.items():
        try:
            resp = client._get("leagues", {"id": api_id})["response"]
            if not resp:
                print(f"{div} -> league_id {api_id}: NO DATA — check the id")
                continue
            info = resp[0]
            print(f"{div} -> league_id {api_id}: {info['league']['name']} "
                  f"({info['country']['name']})")
        except ApiFootballError as e:
            print(f"{div} -> league_id {api_id}: ERROR {e}")


if __name__ == "__main__":
    import sys
    if "--verify-leagues" in sys.argv:
        verify_leagues()
    else:
        print("!" * 72)
        print("PAPER-TRADE / DETECTION MODE. No bets placed, no money at risk.")
        print("!" * 72)
        LiveWatcher().run_once()
