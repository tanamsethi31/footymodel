"""Playwright-based SofaScore client.

Plain HTTP requests to sofascore.com's internal API get 403'd (same
bot-detection this project already hit with WhoScored/FBref) - it only
works from inside a real browser. Verified 2026-08-26: navigate once to
establish a real browser context, then run the site's own fetch() calls
via page.evaluate (same trick already proven for WhoScored).

No API key, no documented daily quota (unlike API-Football) - still worth
being polite about request pacing to avoid tripping bot detection during
an unattended cron.
"""
from __future__ import annotations

import time

from playwright.sync_api import sync_playwright

BASE = "https://www.sofascore.com/api/v1"
MIN_INTERVAL = 1.0


class SofaScoreError(RuntimeError):
    pass


class SofaScoreClient:
    def __init__(self, min_interval: float = MIN_INTERVAL):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._page = self._browser.new_page()
        self._page.goto("https://www.sofascore.com/", wait_until="domcontentloaded")
        self._min_interval = min_interval
        self._last_call = 0.0

    def close(self) -> None:
        self._browser.close()
        self._pw.stop()

    def __enter__(self) -> "SofaScoreClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, path: str, ok_statuses: tuple[int, ...] = (200,)) -> tuple[int, dict]:
        wait = self._min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        js = (
            f"fetch('{BASE}{path}')"
            ".then(r => r.json().then(data => ({status: r.status, data})))"
            ".catch(e => ({status: 0, error: String(e)}))"
        )
        result = self._page.evaluate(js)
        self._last_call = time.monotonic()
        status = result.get("status")
        if status not in ok_statuses:
            raise SofaScoreError(f"{path} -> HTTP {status}: "
                                 f"{result.get('error') or result.get('data')}")
        return status, result["data"]

    def scheduled_events(self, tournament_id: int, date: str) -> list[dict]:
        """Fixtures for one tournament on one date (YYYY-MM-DD). A 404 here
        means no fixtures that day for that league (normal - not every
        league plays every day), not an error."""
        status, data = self._get(f"/unique-tournament/{tournament_id}/scheduled-events/{date}",
                                 ok_statuses=(200, 404))
        return data.get("events", []) if status == 200 else []

    def event(self, event_id: int) -> dict:
        _, data = self._get(f"/event/{event_id}")
        return data.get("event", {})

    def lineups(self, event_id: int) -> dict:
        """{'confirmed': bool, 'home': {'players': [...]}, 'away': {...}}."""
        _, data = self._get(f"/event/{event_id}/lineups")
        return data

    def odds(self, event_id: int) -> list[dict]:
        """Pre-match odds markets. Fractional odds (e.g. '4/9'), not decimal."""
        _, data = self._get(f"/event/{event_id}/odds/1/all")
        return data.get("markets", [])
