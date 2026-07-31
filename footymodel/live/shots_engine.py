"""Live player shots/SOT props — reuses Phase B's fixture/lineup detection and
name-matching (client.py, namematch.py) unchanged, retargeted to output one
row PER STARTING PLAYER (shots + SOT probabilities) instead of one row per
fixture (goals/O-U). PREDICTION ONLY — no odds, no staking; see RESULTS.md
Phase D for why (no reachable historical odds archive for this market).

E0-only for now: SOT (FBref) is PL-only; shots (Understat) covers all big-5
but there's no reason to run it standalone here — SOT is the harder-to-get
half, so scope matches what we can actually deliver both stats for.
"""
from __future__ import annotations

import json

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

    def player_rows_for_fixture(self, fixture: dict, lineups: list[dict]) -> list[dict]:
        """`lineups` is fetched by the caller (run_all.py shares one fetch
        across the goals and player-props watchers, so running both doesn't
        double API-Football usage) — empty/short list means not confirmed yet."""
        fx, teams = fixture["fixture"], fixture["teams"]
        if len(lineups) < 2:
            return []

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
                    key = f"p_shots_gt{line}"
                    row[key] = (round(shots_model.predict_player_shots(u_pid, opp_u, MINUTES_ASSUMED, line, side), 3)
                               if u_pid and opp_u else None)
                for line in SOT_LINES:
                    key = f"p_sot_gt{line}"
                    row[key] = (round(sot_model.predict_player_sot(f_pid, opp_f, MINUTES_ASSUMED, line, side), 3)
                               if f_pid and opp_f else None)
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
    print("PREDICTION ONLY. No odds, no bets, no money at risk.")
    print("!" * 72)
    PropsWatcher().run_once()
