#!/usr/bin/env python3
"""Cloud-side reminder: push when PL fixtures need a home-network SofaScore poll.

SofaScore blocks datacenter IPs, so this cannot run Playwright in GitHub-hosted
runners. It only notifies subscribed phones to start matchday_laptop.sh or wake
the self-hosted runner.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.matchday_status import (
    build_nudge_body,
    fixtures_in_lineup_nudge_window,
    load_calendar,
)


def _read_cooldown(path: Path) -> datetime | None:
    if not path.exists():
        return None
    try:
        return datetime.fromisoformat(path.read_text().strip()).astimezone(timezone.utc)
    except (ValueError, OSError):
        return None


def _write_cooldown(path: Path, when: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(when.astimezone(timezone.utc).isoformat())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cooldown-file",
        type=Path,
        default=Path(".cache/matchday_nudge/last_sent.txt"),
        help="Timestamp of last push (skip if younger than --cooldown-hours)",
    )
    parser.add_argument("--cooldown-hours", type=float, default=3.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    now = pd.Timestamp.now(tz="UTC")
    payload = load_calendar()
    fixtures = fixtures_in_lineup_nudge_window(now, payload)
    if not fixtures:
        print("matchday nudge: no fixtures in lineup window without SofaScore log — skip")
        return 0

    last = _read_cooldown(args.cooldown_file)
    if last is not None:
        age_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        if age_h < args.cooldown_hours:
            print(f"matchday nudge: cooldown ({age_h:.1f}h < {args.cooldown_hours}h) — skip")
            return 0

    url = os.environ.get("NOTIFY_URL")
    secret = os.environ.get("NOTIFY_SECRET")
    if not url or not secret:
        print("NOTIFY_URL/NOTIFY_SECRET not set — would nudge for:", fixtures[0].get("home"))
        return 0

    title = f"Footymodel: home poll needed ({len(fixtures)} fixture(s))"
    body = build_nudge_body(fixtures)

    if args.dry_run:
        print(f"DRY RUN title: {title}")
        print(f"DRY RUN body: {body}")
        return 0

    try:
        resp = requests.post(
            url,
            headers={"x-notify-secret": secret},
            json={"title": title, "body": body, "url": "/"},
            timeout=15,
        )
        resp.raise_for_status()
        _write_cooldown(args.cooldown_file, datetime.now(timezone.utc))
        print(f"matchday nudge sent: {resp.json()}")
    except Exception as e:
        print(f"! matchday nudge failed (non-fatal): {e}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
