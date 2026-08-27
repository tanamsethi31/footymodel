"""Client for the "Free API Live Football Data" RapidAPI listing
(Creativesdev/free-api-live-football-data).

Plain `requests` works fine - no browser/bot-detection issue like SofaScore
or the API-Football suspension. The catch is the free "Basic" plan's quota:
100 requests/MONTH, hard limit (not per-day). See rapidapi_engine.py for how
that's budgeted across the existing 20-min cron.

Verified 2026-08-27 against real fixtures:
  - /football-get-matches-by-date-and-league?date=YYYYMMDD -> ALL leagues
    for that date in one call, grouped by leagueId.
  - /football-get-hometeam-lineup / -awayteam-lineup?eventid=... -> real
    starting XI with confirmed=true/false-equivalent state.
  - /football-event-odds?eventid=...&countrycode=DE -> "Total goals
    over/under" market with a clean "Over 2.5"/"Under 2.5" pair, decimal
    odds already (no fractional conversion needed). countrycode=GB did NOT
    have this market for the same fixture - DE does. Not verified whether
    DE is reliably present for every fixture; the odds lookup treats a
    missing market as "no odds" rather than an error.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

BASE = "https://free-api-live-football-data.p.rapidapi.com"
HOST = "free-api-live-football-data.p.rapidapi.com"

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _load_dotenv() -> None:
    if not _ENV_FILE.exists():
        return
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


class RapidApiError(RuntimeError):
    pass


class RapidApiClient:
    def __init__(self, api_key: str | None = None):
        _load_dotenv()
        self.api_key = api_key or os.environ.get("RAPIDAPI_KEY")
        if not self.api_key:
            raise RapidApiError("No RapidAPI key found. Set RAPIDAPI_KEY env var.")
        self._headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": self.api_key}

    def _get(self, path: str, params: dict) -> dict:
        resp = requests.get(f"{BASE}/{path}", headers=self._headers, params=params, timeout=20)
        if resp.status_code != 200:
            raise RapidApiError(f"{path} -> HTTP {resp.status_code}: {resp.text[:300]}")
        payload = resp.json()
        if payload.get("status") != "success":
            raise RapidApiError(f"{path} -> {payload}")
        return payload["response"]

    def matches_by_date(self, date: str) -> list[dict]:
        """date: YYYYMMDD. Returns ALL leagues for that date in one call,
        each with {id (leagueId), name, matches: [...]}."""
        return self._get("football-get-matches-by-date-and-league", {"date": date})

    def home_lineup(self, event_id: int) -> dict:
        return self._get("football-get-hometeam-lineup", {"eventid": event_id}).get("lineup", {})

    def away_lineup(self, event_id: int) -> dict:
        return self._get("football-get-awayteam-lineup", {"eventid": event_id}).get("lineup", {})

    def odds(self, event_id: int, countrycode: str = "DE") -> dict:
        return self._get("football-event-odds", {"eventid": event_id, "countrycode": countrycode})
