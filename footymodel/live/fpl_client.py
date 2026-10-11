"""Small client for Fantasy Premier League's public fixture feed.

FPL is used only for the Premier League calendar.  It deliberately is not
treated as a lineup or odds provider: those fields are not present in its
public payload.
"""
from __future__ import annotations

import requests


BASE_URL = "https://fantasy.premierleague.com/api"


class FplError(RuntimeError):
    pass


class FplClient:
    def __init__(self, session: requests.Session | None = None):
        self._session = session or requests.Session()

    def _get(self, endpoint: str):
        try:
            response = self._session.get(
                f"{BASE_URL}/{endpoint}", timeout=20,
                headers={"User-Agent": "footymodel-fixture-calendar/1.0"},
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            raise FplError(f"FPL {endpoint} request failed: {e}") from e

    def fixtures(self) -> list[dict]:
        payload = self._get("fixtures/")
        if not isinstance(payload, list):
            raise FplError("FPL fixtures payload was not a list")
        return payload

    def teams(self) -> list[dict]:
        payload = self._get("bootstrap-static/")
        teams = payload.get("teams") if isinstance(payload, dict) else None
        if not isinstance(teams, list):
            raise FplError("FPL bootstrap payload did not contain teams")
        return teams
