"""Live player shots/SOT props — reuses Phase B's fixture/lineup detection and
name-matching (client.py, namematch.py) unchanged, retargeted to output one
row PER STARTING PLAYER (shots + SOT probabilities) instead of one row per
fixture (goals/O-U).

Odds are wired in (Phase I) via the SAME API-Football key already used for
lineups/goals-odds — no new vendor. No historical archive is reachable (Free
tier blocks past-season fixture/odds lookups), so this is forward paper-trade
only: real EV data accumulates once the season starts, same as the goals
engine. Only two bet markets verified to reliably use a clean per-player
"{name} - N+" line format (checked against real bookmaker data): "Player
Shots On Target" and "Home/Away Player Shots". Other shots-named markets seen
in practice are inconsistent (team totals, single-price outrights) and are
deliberately NOT parsed. These are one-sided "N+" lines, not paired
Over/Under, so there's no complement to strip margin from — EV below is the
NAIVE model_prob * odd - 1, uncorrected for bookmaker overround.

E0-only for now: SOT (FBref) is PL-only; shots (Understat) covers all big-5
but there's no reason to run it standalone here — SOT is the harder-to-get
half, so scope matches what we can actually deliver both stats for.
"""
from __future__ import annotations

import json
import re

import pandas as pd

from ..data import PROCESSED_DIR
from ..fbref import SOTModel
from ..fbref import load_players as load_fbref_players
from ..fbref import team_display_names
from ..players import LineupModel, load_players as load_understat_players
from . import namematch
from .client import ApiFootballClient, ApiFootballError
from .engine import LEAGUE_API_IDS

LEAGUE = "E0"
SHOTS_LINES = [0.5, 1.5, 2.5]
SOT_LINES = [0.5, 1.5]
MINUTES_ASSUMED = 85  # measured league-avg starter minutes — see RESULTS.md
PROPS_LOG = PROCESSED_DIR / "live_player_props.csv"
# Standalone-run dedup only (run_all.py shares engine.py's seen-fixtures file
# instead, since it drives both watchers off one fetch per fixture).
PROPS_SEEN_FILE = PROCESSED_DIR / "live_props_seen_fixtures.json"

# API-Football bet-market names verified (2026-07-31, live key) to use a clean
# "{player} - N+" value format. "Player Shots On Target" (242) mixes both
# teams' players in one list; the home/away shots split (240/241) is already
# per-side. Threshold N maps directly onto our existing 0.5/1.5/2.5 lines.
_SHOTS_BET_NAMES = {"Home Player Shots", "Away Player Shots"}
_SOT_BET_NAMES = {"Player Shots On Target"}
_LINE_BY_THRESHOLD = {1: 0.5, 2: 1.5, 3: 2.5}
_PLAYER_LINE_RE = re.compile(r"^(.*) - (\d+)\+$")


def _parse_player_line_odds(odds_response: list[dict], bet_names: set[str]) -> dict:
    """Best (max) odd per (player_name_lower, line) across all bookmakers, for
    the given bet market name(s). Silently skips any value that doesn't match
    the expected "{name} - N+" shape rather than guessing."""
    best: dict[tuple[str, float], float] = {}
    for entry in odds_response:
        for bm in entry.get("bookmakers", []):
            for bet in bm.get("bets", []):
                if bet.get("name") not in bet_names:
                    continue
                for v in bet.get("values", []):
                    m = _PLAYER_LINE_RE.match(str(v.get("value", "")))
                    if not m:
                        continue
                    line = _LINE_BY_THRESHOLD.get(int(m.group(2)))
                    if line is None:
                        continue
                    odd = float(v.get("odd", 0) or 0)
                    if not odd:
                        continue
                    key = (m.group(1).strip().lower(), line)
                    if key not in best or odd > best[key]:
                        best[key] = odd
    return best


def _lookup_player_odd(odds_by_key: dict, player_name: str, line: float) -> float | None:
    """Exact (lowercased) match first; falls back to fuzzy match scoped to the
    other names already seen at this line, since odds-feed spelling doesn't
    always match the lineup-feed spelling for the same player."""
    key = (player_name.lower(), line)
    if key in odds_by_key:
        return odds_by_key[key]
    candidates = [n for (n, l) in odds_by_key if l == line]
    match = namematch.best_match(player_name, candidates, threshold=0.7)
    return odds_by_key.get((match, line)) if match else None


def _load_seen() -> set:
    if PROPS_SEEN_FILE.exists():
        return set(json.loads(PROPS_SEEN_FILE.read_text()))
    return set()


def _save_seen(seen: set) -> None:
    PROPS_SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROPS_SEEN_FILE.write_text(json.dumps(sorted(seen)))


class PropsWatcher:
    def __init__(self, client: ApiFootballClient | None = None):
        self.client = client or ApiFootballClient()
        self.understat = load_understat_players()
        self.fbref = load_fbref_players()
        self.fbref_names = team_display_names(self.fbref)
        self.fbref_name_to_id = {v: k for k, v in self.fbref_names.items()}
        self._shots_model = None
        self._sot_model = None

    def _models(self):
        if self._shots_model is None:
            self._shots_model = LineupModel.fit(self.understat, LEAGUE, pd.Timestamp.now())
            self._sot_model = SOTModel.fit(self.fbref, LEAGUE, pd.Timestamp.now())
        return self._shots_model, self._sot_model

    def _match_team(self, api_name: str) -> tuple[str | None, str | None]:
        """Returns (understat_team_us, fbref_team_us) for an API-Football team name."""
        u_names = namematch.team_name_index(self.understat, LEAGUE)
        u_match = namematch.match_team(api_name, u_names)
        f_match = namematch.match_team(api_name, list(self.fbref_names.values()))
        f_id = self.fbref_name_to_id.get(f_match) if f_match else None
        return u_match, f_id

    def player_rows_for_fixture(self, fixture: dict, lineups: list[dict],
                                odds_resp: list[dict] | None = None) -> list[dict]:
        """`lineups` (and, if given, `odds_resp`) are fetched by the caller
        (run_all.py shares one fetch across the goals and player-props
        watchers, so running both doesn't double API-Football usage) — empty/
        short lineups list means not confirmed yet. `odds_resp=None` fetches
        it here instead, for standalone use."""
        fx, teams = fixture["fixture"], fixture["teams"]
        if len(lineups) < 2:
            return []

        if odds_resp is None:
            try:
                odds_resp = self.client.odds(fx["id"])
            except ApiFootballError as e:
                print(f"  ! odds fetch failed: {e}")
                odds_resp = []
        shots_odds = _parse_player_line_odds(odds_resp, _SHOTS_BET_NAMES)
        sot_odds = _parse_player_line_odds(odds_resp, _SOT_BET_NAMES)

        home_u, home_f = self._match_team(teams["home"]["name"])
        away_u, away_f = self._match_team(teams["away"]["name"])
        by_team_id = {l["team"]["id"]: l for l in lineups}
        home_l, away_l = by_team_id.get(teams["home"]["id"]), by_team_id.get(teams["away"]["id"])
        if home_l is None or away_l is None:
            return []

        shots_model, sot_model = self._models()
        rows = []
        for side_l, team_name, team_u, team_f, opp_u, opp_f, side in [
            (home_l, teams["home"]["name"], home_u, home_f, away_u, away_f, "h"),
            (away_l, teams["away"]["name"], away_u, away_f, home_u, home_f, "a"),
        ]:
            names = [p["player"]["name"] for p in side_l.get("startXI", [])]
            u_roster = namematch.team_roster_index(self.understat, LEAGUE, team_u) if team_u else {}
            f_roster = namematch.team_roster_index(self.fbref, LEAGUE, team_f) if team_f else {}
            for name in names:
                u_pid = namematch.match_player(name, u_roster) if u_roster else None
                f_pid = namematch.match_player(name, f_roster) if f_roster else None
                row = {"fixture_id": fx["id"], "kickoff": fx["date"],
                      "team": team_name, "player": name}
                for line in SHOTS_LINES:
                    p = (round(shots_model.predict_player_shots(u_pid, opp_u, MINUTES_ASSUMED, line, side), 3)
                        if u_pid and opp_u else None)
                    odd = _lookup_player_odd(shots_odds, name, line)
                    row[f"p_shots_gt{line}"] = p
                    row[f"odds_shots_gt{line}"] = odd
                    row[f"ev_shots_gt{line}"] = round(p * odd - 1.0, 3) if (p is not None and odd) else None
                for line in SOT_LINES:
                    p = (round(sot_model.predict_player_sot(f_pid, opp_f, MINUTES_ASSUMED, line, side), 3)
                        if f_pid and opp_f else None)
                    odd = _lookup_player_odd(sot_odds, name, line)
                    row[f"p_sot_gt{line}"] = p
                    row[f"odds_sot_gt{line}"] = odd
                    row[f"ev_sot_gt{line}"] = round(p * odd - 1.0, 3) if (p is not None and odd) else None
                rows.append(row)
        return rows

    def run_once(self, hours_ahead: int = 2) -> list[dict]:
        seen = _load_seen()
        now = pd.Timestamp.now(tz="UTC")
        api_id = LEAGUE_API_IDS[LEAGUE]
        all_rows = []
        for date_str in {now.strftime("%Y-%m-%d"), (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d")}:
            try:
                fixtures = self.client.fixtures_by_date(date_str)
            except ApiFootballError as e:
                print(f"! fixtures fetch failed for {date_str}: {e}")
                continue
            for fx in fixtures:
                if fx["league"]["id"] != api_id:
                    continue
                fid = fx["fixture"]["id"]
                if fid in seen:
                    continue
                kickoff = pd.Timestamp(fx["fixture"]["date"])
                mins_to_ko = (kickoff - now).total_seconds() / 60
                if not (0 <= mins_to_ko <= hours_ahead * 60):
                    continue
                print(f"  checking {fx['teams']['home']['name']} v {fx['teams']['away']['name']}")
                lineups = self.client.lineups(fid)
                rows = self.player_rows_for_fixture(fx, lineups)
                if rows:
                    all_rows.extend(rows)
                    seen.add(fid)

        if all_rows:
            df = pd.DataFrame(all_rows)
            PROPS_LOG.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(PROPS_LOG, mode="a", header=not PROPS_LOG.exists(), index=False)
            print(f"Logged {len(all_rows)} player-prop rows -> {PROPS_LOG}")
        else:
            print("No new confirmed-lineup fixtures this poll.")
        _save_seen(seen)
        return all_rows


if __name__ == "__main__":
    print("!" * 72)
    print("PAPER-TRADE / PREDICTION MODE. No bets placed, no money at risk.")
    print("!" * 72)
    PropsWatcher().run_once()
