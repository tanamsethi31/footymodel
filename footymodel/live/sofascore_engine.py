"""SofaScore-based fallback for the goals/O-U live engine.

API-Football's free-tier account was suspended (see .ladder/ladder.md R019)
with no ETA on reinstatement. SofaScore's own site - not a documented public
API - has confirmed pre-match lineups and Over/Under match-goals odds for
free (verified 2026-08-26). Requires a real browser (see sofascore_client.py
for why); everything downstream of fetching (name-matching, the LineupModel
itself, EV/CLV math) is unchanged from engine.py - only the data source and
transport differ.

No player-prop odds exist anywhere on SofaScore (checked) - this replaces
only the goals/O-U engine, not shots_engine.py. Runs independently of
live/engine.py and run_all.py: those keep polling API-Football as-is
(a harmless no-op while suspended) and resume automatically if/when it's
reinstated. Logs to the SAME live_recommendations.csv, tagged
source="sofascore", with its own seen-fixtures file so the two engines
never collide.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

from ..data import PROCESSED_DIR
from ..players import LineupModel, load_players
from ..strategy import remove_margin
from . import namematch
from .sofascore_client import SofaScoreClient, SofaScoreError

# Only E0 - the one league with individually significant backtested
# evidence for the full-lineup model (RESULTS.md Phase A: E0 t=2.23 alone;
# the pooled t=3.04 across all big-5 leans on E0, the others don't clear
# significance on their own). div code -> SofaScore unique-tournament id,
# verified 2026-08-26 via /api/v1/search/unique-tournaments.
TOURNAMENT_IDS = {
    "E0": 17,   # Premier League
}

LIVE_LOG = PROCESSED_DIR / "live_recommendations.csv"
SEEN_FIXTURES_FILE = PROCESSED_DIR / "sofascore_seen_fixtures.json"

# Lineups confirm ~20-40min pre-kickoff on API-Football; SofaScore's timing
# hasn't been characterized as precisely, so keep the same 2hr lookback -
# a poll well before confirmation just gets confirmed=false and retries.
DEFAULT_HOURS_AHEAD = 2


def _load_seen() -> set:
    if SEEN_FIXTURES_FILE.exists():
        return set(json.loads(SEEN_FIXTURES_FILE.read_text()))
    return set()


def _save_seen(seen: set) -> None:
    SEEN_FIXTURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FIXTURES_FILE.write_text(json.dumps(sorted(seen)))


def _frac_to_decimal(fractional: str) -> float:
    """SofaScore quotes fractional odds ('4/9'); decimal = num/den + 1."""
    return float(Fraction(fractional)) + 1.0


def _find_25_line(markets: list[dict]) -> tuple[float | None, float | None]:
    for m in markets:
        if m.get("marketGroup") != "Match goals" or m.get("choiceGroup") != "2.5":
            continue
        over = under = None
        for c in m.get("choices", []):
            val = _frac_to_decimal(c["fractionalValue"])
            if c["name"] == "Over":
                over = val
            elif c["name"] == "Under":
                under = val
        return over, under
    return None, None


class SofaScoreWatcher:
    def __init__(self, client: SofaScoreClient):
        self.client = client
        self.players = load_players()
        self._models: dict[str, LineupModel] = {}
        self._team_rosters: dict[tuple, dict] = {}

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

    def process_fixture(self, league: str, event: dict) -> dict | None:
        event_id = event["id"]
        home_api, away_api = event["homeTeam"]["name"], event["awayTeam"]["name"]

        lineups = self.client.lineups(event_id)
        if not lineups.get("confirmed"):
            return None  # not confirmed yet - caller will retry on next poll

        team_names = namematch.team_name_index(self.players, league)
        home_us = namematch.match_team(home_api, team_names)
        away_us = namematch.match_team(away_api, team_names)
        if not home_us or not away_us:
            print(f"  ! team-name match failed: {home_api} / {away_api}")
            return None

        home_names = [p["player"]["name"] for p in lineups.get("home", {}).get("players", [])
                     if p.get("substitute") is False]
        away_names = [p["player"]["name"] for p in lineups.get("away", {}).get("players", [])
                     if p.get("substitute") is False]
        home_ids = self.map_lineup_to_ids(league, home_us, home_names)
        away_ids = self.map_lineup_to_ids(league, away_us, away_names)
        if len(home_ids) < 8 or len(away_ids) < 8:  # too many unmatched to trust
            print(f"  ! too few matched starters ({len(home_ids)}/{len(away_ids)}) "
                  f"for {home_api} v {away_api}, skipping")
            return None

        model = self._model_for(league)
        pred = model.predict(home_ids, away_ids, home_us, away_us)

        try:
            markets = self.client.odds(event_id)
        except SofaScoreError as e:
            print(f"  ! odds fetch failed: {e}")
            markets = []
        over_odds, under_odds = _find_25_line(markets)

        row = {
            "logged_at": pd.Timestamp.now().isoformat(),
            "fixture_id": f"sofa_{event_id}", "league": league,
            "kickoff": pd.Timestamp(event["startTimestamp"], unit="s", tz="UTC").isoformat(),
            "home": home_api, "away": away_api,
            "n_home_starters_matched": len(home_ids), "n_away_starters_matched": len(away_ids),
            "model_p_over25": round(pred["p_over25_blend"], 3),
            "exp_total_goals": round(pred["exp_blend"], 2),
            "odds_over25": over_odds, "odds_under25": under_odds,
            "source": "sofascore",
        }
        if over_odds and under_odds:
            fair = remove_margin(np.array([over_odds, under_odds]))
            row["fair_p_over25"] = round(float(fair[0]), 3)
            row["ev_over25"] = round(pred["p_over25_blend"] * over_odds - 1.0, 3)
            row["ev_under25"] = round((1 - pred["p_over25_blend"]) * under_odds - 1.0, 3)
        return row

    def run_once(self, hours_ahead: int = DEFAULT_HOURS_AHEAD) -> list[dict]:
        seen = _load_seen()
        now = pd.Timestamp.now(tz="UTC")
        new_rows = []

        for date_str in {now.strftime("%Y-%m-%d"), (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d")}:
            for div, tid in TOURNAMENT_IDS.items():
                try:
                    events = self.client.scheduled_events(tid, date_str)
                except SofaScoreError as e:
                    print(f"! fixtures fetch failed for {div} {date_str}: {e}")
                    continue
                for ev in events:
                    if ev.get("status", {}).get("type") != "notstarted":
                        continue
                    eid = ev["id"]
                    if eid in seen:
                        continue
                    kickoff = pd.Timestamp(ev["startTimestamp"], unit="s", tz="UTC")
                    mins_to_ko = (kickoff - now).total_seconds() / 60
                    if not (0 <= mins_to_ko <= hours_ahead * 60):
                        continue
                    print(f"  checking {ev['homeTeam']['name']} v {ev['awayTeam']['name']} "
                          f"(kickoff in {mins_to_ko:.0f}min)")
                    try:
                        row = self.process_fixture(div, ev)
                    except Exception as e:
                        print(f"  ! error processing event {eid}: {e}")
                        continue
                    if row is not None:
                        new_rows.append(row)
                        seen.add(eid)

        if new_rows:
            df = pd.DataFrame(new_rows)
            LIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(LIVE_LOG, mode="a", header=not LIVE_LOG.exists(), index=False)
            print(f"Logged {len(new_rows)} new recommendation(s) -> {LIVE_LOG}")
        else:
            print("No new confirmed-lineup fixtures this poll (SofaScore).")
        _save_seen(seen)
        return new_rows


if __name__ == "__main__":
    import traceback

    print("!" * 72)
    print("PAPER-TRADE / PREDICTION MODE (SofaScore source). No bets placed, no money at risk.")
    print("!" * 72)
    try:
        with SofaScoreClient() as client:
            SofaScoreWatcher(client).run_once()
    except Exception:
        print("!" * 72)
        print("CRON RUN FAILED - nothing was logged this poll. Traceback:")
        print("!" * 72)
        traceback.print_exc()
        raise
