#!/usr/bin/env python3
"""Print upcoming PL kickoffs and when live polls are expected to run (Irish time)."""
from __future__ import annotations

import json
from zoneinfo import ZoneInfo

import pandas as pd

from footymodel.data import PROCESSED_DIR
from footymodel.live.calendar import CALENDAR_FILE, load_calendar
from footymodel.live.engine import DEFAULT_HOURS_AHEAD, DEFAULT_HOURS_BEHIND

DUBLIN = ZoneInfo("Europe/Dublin")


def _fmt(ts: pd.Timestamp) -> str:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.tz_convert(DUBLIN).strftime("%a %d %b %Y %H:%M %Z")


def main() -> None:
    payload = load_calendar()
    fixtures = payload.get("fixtures") or []
    if not fixtures and CALENDAR_FILE.exists():
        fixtures = json.loads(CALENDAR_FILE.read_text()).get("fixtures") or []

    now = pd.Timestamp.now(tz="UTC")
    lo = -DEFAULT_HOURS_BEHIND * 60
    hi = DEFAULT_HOURS_AHEAD * 60

    print(f"Now (Irish): {_fmt(now)}")
    print(
        f"Live window: {DEFAULT_HOURS_BEHIND}h before kickoff → "
        f"{DEFAULT_HOURS_AHEAD}h after (calendar gate)\n"
    )

    rows = []
    for rec in fixtures:
        ko = pd.Timestamp(rec["kickoff"])
        if ko.tzinfo is None:
            ko = ko.tz_localize("UTC")
        mins = (ko - now).total_seconds() / 60
        rows.append((mins, rec, ko))

    rows.sort(key=lambda x: x[0])
    upcoming = [r for r in rows if r[0] > -DEFAULT_HOURS_BEHIND * 60][:15]
    if not upcoming:
        print("No upcoming fixtures in calendar (refresh with live_poll or calendar --refresh).")
        return

    print("Next fixtures:")
    next_ko = None
    for mins, rec, ko in upcoming:
        in_window = lo <= mins <= hi
        flag = "← POLL WINDOW" if in_window else ""
        print(
            f"  {_fmt(ko)}  {rec['home']} v {rec['away']}  "
            f"({mins:+.0f} min) {flag}"
        )
        if next_ko is None and mins > 15:
            next_ko = (mins, rec, ko)

    if next_ko:
        mins, rec, ko = next_ko
        sweet_start = ko - pd.Timedelta(minutes=90)
        sweet_end = ko - pd.Timedelta(minutes=15)
        print(
            f"\nHome poll (goals O/U + props, Wi‑Fi): ./scripts/matchday_laptop.sh loop 900 --push "
            f"from {_fmt(sweet_start)} until lineups land (ideally before {_fmt(sweet_end)})."
        )
        print(
            "  Phone calendar: subscribe to data/processed/matchday_reminders.ics "
            "(refreshed by live_poll.yml on GitHub)."
        )
        if mins > 90:
            wait_min = int(mins - 90)
            print(f"  Next match is {wait_min} min until the usual T−90 window.")

    print(
        "\nCloud (laptop off): calendar + grading on GitHub Actions."
    )
    print("Post-match grading: grade_props.yml at 08:00 & 23:30 UTC.")


if __name__ == "__main__":
    main()
