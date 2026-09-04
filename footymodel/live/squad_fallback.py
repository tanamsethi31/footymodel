"""Apify teamSquad fallback for pre-lineup player props previews.

When a team has no current-season Understat starts yet (early campaign,
promoted sides, etc.), `recent_non_gk_starters` returns empty and the
dashboard watchlist would show no away/home names. This module fetches the
live SofaScore squad via Apify and maps names onto our Understat player ids
so the shots model can still rank candidates.

Runs are cached per team for a week and capped monthly so daily watchlist
refreshes stay cheap.
"""
from __future__ import annotations

import json

import pandas as pd

from ..data import PROCESSED_DIR
from . import namematch
from .apify_client import ApifyFootballClient, ApifyError
from .apify_engine import SEASON_IDS, TOURNAMENT_IDS

SQUAD_CACHE_FILE = PROCESSED_DIR / "apify_squad_cache.json"
TEAM_IDS_FILE = PROCESSED_DIR / "apify_team_ids.json"
SQUAD_BUDGET_FILE = PROCESSED_DIR / "apify_squad_budget.json"

SQUAD_CACHE_DAYS = 7
SQUAD_RUNS_CAP = 40  # teamSquad Actor starts/month (watchlist-only)
GK_POSITIONS = frozenset({"G", "GK"})


def _month_key() -> str:
    return pd.Timestamp.now(tz="UTC").strftime("%Y-%m")


def _load_squad_budget() -> dict:
    month = _month_key()
    if SQUAD_BUDGET_FILE.exists():
        b = json.loads(SQUAD_BUDGET_FILE.read_text())
        if b.get("month") == month:
            return b
    return {"month": month, "runs_used": 0}


def _save_squad_budget(budget: dict) -> None:
    SQUAD_BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    SQUAD_BUDGET_FILE.write_text(json.dumps(budget))


def _load_squad_cache() -> dict:
    if not SQUAD_CACHE_FILE.exists():
        return {}
    return json.loads(SQUAD_CACHE_FILE.read_text())


def _save_squad_cache(cache: dict) -> None:
    SQUAD_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SQUAD_CACHE_FILE.write_text(json.dumps(cache))


def _load_team_ids() -> dict | None:
    if not TEAM_IDS_FILE.exists():
        return None
    payload = json.loads(TEAM_IDS_FILE.read_text())
    if payload.get("month") != _month_key():
        return None
    return payload.get("by_name") or {}


def _save_team_ids(by_name: dict[str, int]) -> None:
    TEAM_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEAM_IDS_FILE.write_text(json.dumps({"month": _month_key(), "by_name": by_name}))


def _is_fresh(fetched_at: str, days: int = SQUAD_CACHE_DAYS) -> bool:
    try:
        ts = pd.Timestamp(fetched_at)
    except (TypeError, ValueError):
        return False
    age = pd.Timestamp.now(tz="UTC") - ts.tz_localize("UTC") if ts.tzinfo is None else pd.Timestamp.now(tz="UTC") - ts
    return age.days < days


def _parse_squad_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if r.get("status") not in (None, "success"):
            continue
        name = r.get("playerName") or r.get("name")
        if not name:
            continue
        pos = str(r.get("playerPosition") or r.get("position") or "")
        out.append({"playerName": str(name), "position": pos})
    return out


class SquadFallback:
    """Optional Apify-backed squad source; no-ops when token missing or cap hit."""

    def __init__(
        self,
        client: ApifyFootballClient | None = None,
        budget: dict | None = None,
        squad_cache: dict | None = None,
        team_ids: dict[str, int] | None = None,
    ):
        self._client = client
        self._budget = budget if budget is not None else _load_squad_budget()
        self._squad_cache = squad_cache if squad_cache is not None else _load_squad_cache()
        self._team_ids = team_ids if team_ids is not None else _load_team_ids()
        self._rosters: dict[tuple, dict] = {}

    @classmethod
    def try_create(cls) -> "SquadFallback | None":
        try:
            return cls(client=ApifyFootballClient())
        except ApifyError as e:
            print(f"  watchlist squad fallback disabled: {e}")
            return None

    def _spend(self) -> bool:
        if self._budget["runs_used"] >= SQUAD_RUNS_CAP:
            return False
        self._budget["runs_used"] += 1
        _save_squad_budget(self._budget)
        return True

    def _roster_for(self, players: pd.DataFrame, league: str, team_us: str) -> dict:
        key = (league, team_us)
        if key not in self._rosters:
            self._rosters[key] = namematch.team_roster_index(players, league, team_us)
        return self._rosters[key]

    def _ensure_team_ids(self, league: str) -> dict[str, int]:
        if self._team_ids is not None:
            return self._team_ids
        if self._client is None or not self._spend():
            self._team_ids = {}
            return self._team_ids
        tid = TOURNAMENT_IDS.get(league)
        sid = SEASON_IDS.get(league)
        if tid is None or sid is None:
            self._team_ids = {}
            return self._team_ids
        try:
            rows = self._client.league_fixtures(tid, sid, span="next", max_results=80)
        except ApifyError as e:
            print(f"  ! squad team-id scan failed: {e}")
            self._team_ids = {}
            return self._team_ids
        by_name: dict[str, int] = {}
        for r in rows:
            for name_key, id_key in (
                ("homeTeamName", "homeTeamId"),
                ("awayTeamName", "awayTeamId"),
            ):
                name = r.get(name_key)
                team_id = r.get(id_key)
                if name and team_id is not None:
                    by_name[str(name)] = int(team_id)
        self._team_ids = by_name
        _save_team_ids(by_name)
        print(f"  squad fallback: cached {len(by_name)} team name(s) for {league}")
        return self._team_ids

    def resolve_team_id(self, league: str, api_team_name: str) -> int | None:
        by_name = self._ensure_team_ids(league)
        if not by_name:
            return None
        match = namematch.best_match(api_team_name, list(by_name.keys()), threshold=0.55)
        return by_name.get(match) if match else None

    def _fetch_squad(self, team_id: int) -> list[dict]:
        key = str(team_id)
        cached = self._squad_cache.get(key)
        if cached and _is_fresh(cached.get("fetched_at", "")):
            return cached.get("players") or []
        if self._client is None or not self._spend():
            return cached.get("players") if cached else []
        try:
            rows = self._client.team_squad(team_id)
        except ApifyError as e:
            print(f"  ! teamSquad({team_id}) failed: {e}")
            return cached.get("players") if cached else []
        players = _parse_squad_rows(rows)
        self._squad_cache[key] = {
            "fetched_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "players": players,
        }
        _save_squad_cache(self._squad_cache)
        return players

    def candidates(
        self,
        players: pd.DataFrame,
        league: str,
        team_us: str,
        api_team_name: str,
    ) -> list[tuple]:
        """`(player_id, display_name)` from live squad, excluding goalkeepers."""
        if self._client is None:
            return []
        team_id = self.resolve_team_id(league, api_team_name)
        if team_id is None:
            return []
        squad = self._fetch_squad(team_id)
        if not squad:
            return []
        roster = self._roster_for(players, league, team_us)
        id_to_name = {pid: name for name, pid in roster.items()}
        out: list[tuple] = []
        seen: set = set()
        for row in squad:
            if row["position"] in GK_POSITIONS:
                continue
            pid = namematch.match_player(row["playerName"], roster)
            if pid is None or pid in seen:
                continue
            seen.add(pid)
            out.append((pid, id_to_name.get(pid, row["playerName"])))
        return out


def augment_candidates(
    starters: list[tuple],
    *,
    players: pd.DataFrame,
    league: str,
    team_us: str,
    api_team_name: str,
    squad: SquadFallback | None,
) -> list[tuple]:
    """Prefer current-season starters; fill from Apify squad when empty."""
    if starters:
        return starters
    if squad is None:
        return []
    return squad.candidates(players, league, team_us, api_team_name)
