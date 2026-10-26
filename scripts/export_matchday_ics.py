#!/usr/bin/env python3
"""Export PL kickoffs + T−90 reminders as ICS for Google/Apple Calendar."""
from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.data import PROCESSED_DIR
from footymodel.live.calendar import load_calendar

DUBLIN = ZoneInfo("Europe/Dublin")
OUT = PROCESSED_DIR / "matchday_reminders.ics"


def _ics_dt(ts: pd.Timestamp) -> str:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.strftime("%Y%m%dT%H%M%SZ")


def main() -> None:
    payload = load_calendar() or {}
    fixtures = payload.get("fixtures") or []
    now = pd.Timestamp.now(tz="UTC")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//footymodel//matchday//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:Footymodel PL matchday",
    ]
    uid = 0
    for rec in fixtures:
        ko = pd.Timestamp(rec["kickoff"])
        if ko.tzinfo is None:
            ko = ko.tz_localize("UTC")
        if ko < now - pd.Timedelta(days=1):
            continue
        home, away = rec.get("home", "?"), rec.get("away", "?")
        poll_start = ko - pd.Timedelta(minutes=90)
        uid += 1
        summary = f"Footymodel poll: {home} v {away}"
        desc = (
            "Start on home Wi-Fi:\\n"
            "./scripts/matchday_laptop.sh loop 900 --push\\n"
            "Or trigger self-hosted workflow live_poll_props_selfhosted.yml"
        )
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:footymodel-{uid}@local",
                f"DTSTAMP:{_ics_dt(now)}",
                f"DTSTART:{_ics_dt(poll_start)}",
                f"DTEND:{_ics_dt(ko)}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                "END:VEVENT",
            ]
        )
        # Kickoff marker
        uid += 1
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:footymodel-ko-{uid}@local",
                f"DTSTAMP:{_ics_dt(now)}",
                f"DTSTART:{_ics_dt(ko)}",
                f"DTEND:{_ics_dt(ko + pd.Timedelta(hours=2))}",
                f"SUMMARY:KO {home} v {away}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    local = now.tz_convert(DUBLIN).strftime("%Y-%m-%d %H:%M %Z")
    print(f"Wrote {OUT} ({uid} events) at {local}")


if __name__ == "__main__":
    main()
