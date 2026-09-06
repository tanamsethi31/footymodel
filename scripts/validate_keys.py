#!/usr/bin/env python3
"""Check API keys from .env / environment and print actionable status."""
from __future__ import annotations

import os
import sys

from footymodel.live.apify_client import ApifyFootballClient, ApifyError
from footymodel.live.client import ApiFootballClient, ApiFootballError
from footymodel.live.rapidapi_client import RapidApiClient, RapidApiError


def _status(name: str, ok: bool, detail: str = "") -> None:
    mark = "OK" if ok else "MISSING/INVALID"
    extra = f" — {detail}" if detail else ""
    print(f"  {name}: {mark}{extra}")


def main() -> int:
    print("API key check (reads .env via each client):")
    failed = 0

    try:
        ApiFootballClient().get("/status")
        _status("API_FOOTBALL_KEY", True)
    except ApiFootballError as e:
        _status("API_FOOTBALL_KEY", False, str(e))
        failed += 1
    except Exception as e:
        _status("API_FOOTBALL_KEY", False, str(e))
        failed += 1

    try:
        RapidApiClient()
        _status("RAPIDAPI_KEY", True, "loaded")
    except RapidApiError as e:
        _status("RAPIDAPI_KEY", False, str(e))
        failed += 1

    try:
        ApifyFootballClient().run("leagueSeasons", tournamentId=17)
        _status("APIFY_TOKEN", True)
    except ApifyError as e:
        _status("APIFY_TOKEN", False, str(e))
        failed += 1

    if os.environ.get("NOTIFY_SECRET"):
        _status("NOTIFY_SECRET", True, "set")
    else:
        _status("NOTIFY_SECRET", False, "optional for local runs")

    if failed:
        print()
        print("Fix GitHub Actions secrets: repo Settings → Secrets and variables → Actions")
        print("  gh secret set -f .env   (requires repo admin)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
