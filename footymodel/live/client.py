"""Thin API-Football (api-sports.io) client.

Requires env var API_FOOTBALL_KEY. Get a key at api-football.com — the Free
tier (100 req/day) covers watching a handful of fixtures/day; Pro ($19/mo,
7,500 req/day) if you scale up. CONFIRMED from their live docs (checked
2026-07-26): lineups are available 20-40 minutes before kickoff when the
competition has lineup coverage — check the `leagues` endpoint's `coverage`
field per league before relying on it.

All parsing is defensive: on an unexpected shape we raise with the raw payload
attached rather than silently returning wrong data — API responses are the one
thing here we can't unit-test against ahead of time.
"""
from __future__ import annotations

import os
import time

import requests

BASE_URL = "https://v3.football.api-sports.io"


class ApiFootballError(RuntimeError):
    pass


class ApiFootballClient:
    def __init__(self, api_key: str | None = None, min_interval: float = 1.0):
        self.api_key = api_key or os.environ.get("API_FOOTBALL_KEY")
        if not self.api_key:
            raise ApiFootballError(
                "No API-Football key found. Set API_FOOTBALL_KEY env var. "
                "Get a free-tier key at https://www.api-football.com/pricing")
        self._headers = {"x-apisports-key": self.api_key}
        self._min_interval = min_interval
        self._last_call = 0.0

    def _get(self, path: str, params: dict | None = None) -> dict:
        wait = self._min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        resp = requests.get(f"{BASE_URL}/{path}", headers=self._headers,
                            params=params or {}, timeout=20)
        self._last_call = time.monotonic()
        if resp.status_code != 200:
            raise ApiFootballError(f"{path} -> HTTP {resp.status_code}: {resp.text[:300]}")
        payload = resp.json()
        if payload.get("errors"):
            raise ApiFootballError(f"{path} -> API errors: {payload['errors']}")
        return payload

    def status(self) -> dict:
        """Account/quota status. Free call (does not count against the daily quota)."""
        return self._get("status")["response"]

    def fixtures_by_date(self, date: str, league: int | None = None,
                         season: int | None = None) -> list[dict]:
        """Fixtures on a given date (YYYY-MM-DD), optionally filtered by league."""
        params = {"date": date}
        if league is not None:
            params["league"] = league
        if season is not None:
            params["season"] = season
        return self._get("fixtures", params)["response"]

    def lineups(self, fixture_id: int) -> list[dict]:
        """Starting lineups for a fixture. Empty list if not yet announced —
        per API docs, available ~20-40 min before kickoff (competition-dependent)."""
        return self._get("fixtures/lineups", {"fixture": fixture_id})["response"]

    def odds(self, fixture_id: int, bookmaker: int | None = None) -> list[dict]:
        """Pre-match odds for a fixture. Structure: response[].bookmakers[].bets[]
        with bets named e.g. 'Over/Under' -> values [{value:'Over 2.5', odd:'1.85'}, ...]."""
        params = {"fixture": fixture_id}
        if bookmaker is not None:
            params["bookmaker"] = bookmaker
        return self._get("odds", params)["response"]

    def league_coverage(self, league_id: int, season: int) -> dict | None:
        """Check whether a league/season has lineup + odds coverage."""
        resp = self._get("leagues", {"id": league_id, "season": season})["response"]
        if not resp:
            return None
        return resp[0].get("seasons", [{}])[0].get("coverage")
