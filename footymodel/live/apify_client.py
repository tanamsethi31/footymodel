"""Apify client for sian.agency/football-api-scraper.

Uses Apify's run-sync-get-dataset-items endpoint so GitHub Actions can
await one Actor run and read rows without polling. Requires APIFY_TOKEN
(from https://console.apify.com/account/integrations).

This is a resilient access path to SofaScore-shaped football data (fixtures,
confirmed lineups, match-goals odds) when direct Playwright scraping 403s.
Verified 2026-09-04 via the Apify MCP connector.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

ACTOR_ID = "sian.agency~football-api-scraper"
BASE_URL = "https://api.apify.com/v2"
SYNC_TIMEOUT_SECS = 120

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


class ApifyError(RuntimeError):
    pass


class ApifyFootballClient:
    def __init__(self, token: str | None = None):
        _load_dotenv()
        self.token = token or os.environ.get("APIFY_TOKEN")
        if not self.token:
            raise ApifyError(
                "No Apify token found. Set APIFY_TOKEN env var. "
                "Create one at https://console.apify.com/account/integrations"
            )

    def run(self, operation: str, **kwargs) -> list[dict]:
        """Run one Actor operation and return dataset rows."""
        payload = {"operation": operation, **kwargs}
        url = f"{BASE_URL}/acts/{ACTOR_ID}/run-sync-get-dataset-items"
        resp = requests.post(
            url,
            params={"token": self.token, "timeout": SYNC_TIMEOUT_SECS},
            json=payload,
            timeout=SYNC_TIMEOUT_SECS + 15,
        )
        if resp.status_code not in (200, 201):
            raise ApifyError(
                f"{operation} -> HTTP {resp.status_code}: {resp.text[:400]}"
            )
        data = resp.json()
        if not isinstance(data, list):
            raise ApifyError(f"{operation} -> unexpected payload type: {type(data)}")
        failed = [r for r in data if r.get("status") not in (None, "success")]
        if failed and not any(r.get("status") == "success" for r in data):
            raise ApifyError(f"{operation} -> all rows failed: {failed[0]}")
        return data

    def league_fixtures(
        self,
        tournament_id: int,
        season_id: int,
        span: str = "next",
        max_pages: int = 1,
        max_results: int = 40,
    ) -> list[dict]:
        return self.run(
            "leagueFixtures",
            tournamentId=tournament_id,
            seasonId=season_id,
            span=span,
            maxPages=max_pages,
            maxResults=max_results,
        )

    def match_lineups(self, match_id: int) -> list[dict]:
        return self.run("matchLineups", matchId=match_id)

    def match_odds(self, match_id: int) -> list[dict]:
        return self.run("matchOdds", matchId=match_id)
