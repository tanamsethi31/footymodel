"""Premier League fixture calendar: saved in advance, used to (1) show the
next matchweek on the dashboard even when nothing kicks off in the next
3 days, and (2) skip the expensive live engines (API-Football lineups/odds,
SofaScore Playwright, RapidAPI) on polls where no tracked fixture is inside
the live window.

Why this exists: GitHub Actions is scheduled every 20 minutes 09:00-21:59 UTC,
but in practice those scheduled triggers slip by hours (see the fixture-window
design spec). Meanwhile each idle poll still spent ~1 minute installing
Playwright and 3 API-Football date-bucket calls, for a 3-day upcoming list
that is empty most midweeks. RapidAPI already caches today's fixtures for
the same reason; this is that idea for the primary engine, with a 10-day
horizon so the dashboard preview isn't stuck to a 3-day look-ahead.

The calendar is NOT a substitute for the live fixtures fetch on a real
match poll — kickoff times move. It only gates whether to run, and which
extra date buckets to fetch so a delayed poll can still see yesterday's
unseen fixtures (DEFAULT_HOURS_BEHIND is useless if that date isn't queried).

Fail open: a missing or stale calendar always runs the live engines rather
than risk missing a lineup window.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import pandas as pd

from ..data import PROCESSED_DIR
from ..understat import RAW_XG_DIR
from .client import ApiFootballClient, ApiFootballError
from .engine import (DEFAULT_HOURS_AHEAD, DEFAULT_HOURS_BEHIND, LEAGUE_API_IDS,
                     _load_seen)

CALENDAR_FILE = PROCESSED_DIR / "fixture_calendar.json"
UPCOMING_LOG = PROCESSED_DIR / "upcoming_fixtures.json"
# Overridable in tests so dry-runs don't pick up the real EPL cache.
UNDERSTAT_DIR = RAW_XG_DIR

# 10 days covers a typical PL matchweek plus an international-break midweek
# without spending a date-query per poll. 0..horizon inclusive = 11 calls
# when a refresh actually runs (once a day, not every 20 min).
HORIZON_DAYS = 10
MAX_AGE_HOURS = 36


def _as_utc(ts: pd.Timestamp) -> pd.Timestamp:
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def utc_date_str(iso_or_ts) -> str:
    return _as_utc(pd.Timestamp(iso_or_ts)).strftime("%Y-%m-%d")


def match_key(row: dict) -> tuple[str, str, str]:
    """Collapse API-Football and Understat rows for the same fixture.
    Kickoff compared on the UTC calendar day so a timezone suffix vs a
    naive Understat datetime still matches."""
    kickoff = utc_date_str(row["kickoff"])
    return (str(row["home"]).strip().lower(),
            str(row["away"]).strip().lower(),
            kickoff)


def understat_season_year(now: pd.Timestamp) -> int:
    """Understat's season label is the starting year (2026 -> 2026/27)."""
    now = _as_utc(now)
    return int(now.year if now.month >= 7 else now.year - 1)


def load_calendar() -> dict[str, Any] | None:
    if not CALENDAR_FILE.exists():
        return None
    try:
        payload = json.loads(CALENDAR_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def save_calendar(payload: dict[str, Any]) -> None:
    CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
    CALENDAR_FILE.write_text(json.dumps(payload, indent=2))


def calendar_is_fresh(now: pd.Timestamp | None = None,
                      max_age_hours: int = MAX_AGE_HOURS,
                      payload: dict[str, Any] | None = None) -> bool:
    payload = payload if payload is not None else load_calendar()
    if not payload or not payload.get("refreshed_at"):
        return False
    now = _as_utc(now if now is not None else pd.Timestamp.now(tz="UTC"))
    refreshed = _as_utc(pd.Timestamp(payload["refreshed_at"]))
    return (now - refreshed).total_seconds() <= max_age_hours * 3600


def fixtures_in_live_window(
    now: pd.Timestamp | None = None,
    payload: dict[str, Any] | None = None,
    hours_ahead: int = DEFAULT_HOURS_AHEAD,
    hours_behind: int = DEFAULT_HOURS_BEHIND,
) -> list[dict]:
    """Calendar records whose kickoff is inside the same window run_all.py
    uses for lineup/odds fetches."""
    payload = payload if payload is not None else load_calendar()
    if not payload:
        return []
    now = _as_utc(now if now is not None else pd.Timestamp.now(tz="UTC"))
    lo = -hours_behind * 60
    hi = hours_ahead * 60
    out = []
    for rec in payload.get("fixtures") or []:
        try:
            kickoff = _as_utc(pd.Timestamp(rec["kickoff"]))
        except (KeyError, TypeError, ValueError):
            continue
        mins = (kickoff - now).total_seconds() / 60
        if lo <= mins <= hi:
            out.append(rec)
    return out


def upcoming_from_calendar(now: pd.Timestamp | None = None,
                           payload: dict[str, Any] | None = None) -> list[dict]:
    """Dashboard preview records for every calendar fixture that hasn't
    kicked off yet — not limited to the live 3-day API window."""
    payload = payload if payload is not None else load_calendar()
    if not payload:
        return []
    now = _as_utc(now if now is not None else pd.Timestamp.now(tz="UTC"))
    upcoming = []
    seen_ids: set = set()
    for rec in payload.get("fixtures") or []:
        fid = rec.get("fixture_id")
        home, away, kickoff = rec.get("home"), rec.get("away"), rec.get("kickoff")
        if fid is None or not home or not away or not kickoff:
            continue
        try:
            if _as_utc(pd.Timestamp(kickoff)) <= now:
                continue
        except (TypeError, ValueError):
            continue
        if fid in seen_ids:
            continue
        seen_ids.add(fid)
        upcoming.append({
            "fixture_id": fid,
            "home": home,
            "away": away,
            "kickoff": kickoff,
        })
    upcoming.sort(key=lambda r: (r["kickoff"], r["home"]))
    return upcoming


def upcoming_from_understat(now: pd.Timestamp | None = None,
                            horizon_days: int = HORIZON_DAYS,
                            year: int | None = None) -> list[dict]:
    """Next PL fixtures from the already-cached Understat season file.
    No API-Football key, so the dashboard preview still fills on a day
    the API calendar refresh can't run. IDs are prefixed `us_` so they
    never collide with API-Football fixture ids used for gating/`seen`."""
    now = _as_utc(now if now is not None else pd.Timestamp.now(tz="UTC"))
    year = year if year is not None else understat_season_year(now)
    path = UNDERSTAT_DIR / f"EPL_{year}.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    horizon_end = now + pd.Timedelta(days=horizon_days)
    upcoming = []
    seen_ids: set = set()
    for rec in payload.get("dates") or []:
        if not isinstance(rec, dict) or rec.get("isResult"):
            continue
        try:
            kickoff = pd.Timestamp(rec["datetime"])
            kickoff = _as_utc(kickoff)
            home = rec["h"]["title"]
            away = rec["a"]["title"]
            uid = rec["id"]
        except (KeyError, TypeError, ValueError):
            continue
        if kickoff <= now or kickoff > horizon_end:
            continue
        fid = f"us_{uid}"
        if fid in seen_ids:
            continue
        seen_ids.add(fid)
        upcoming.append({
            "fixture_id": fid,
            "home": home,
            "away": away,
            "kickoff": kickoff.isoformat(),
        })
    upcoming.sort(key=lambda r: (r["kickoff"], r["home"]))
    return upcoming


def merge_upcoming(primary: list[dict], extra: list[dict]) -> list[dict]:
    """Union by fixture_id OR (home, away, UTC date). `primary` wins —
    live API-Football rows beat a calendar snapshot, which beats Understat
    `us_` placeholders for the same match."""
    selected: list[dict] = []

    def upsert(row: dict) -> None:
        k = match_key(row)
        fid = row["fixture_id"]
        selected[:] = [r for r in selected
                       if match_key(r) != k and r["fixture_id"] != fid]
        selected.append(row)

    for row in extra:
        upsert(row)
    for row in primary:
        upsert(row)
    return sorted(selected, key=lambda r: (r["kickoff"], r["home"]))


def date_buckets_to_fetch(
    now: pd.Timestamp | None = None,
    payload: dict[str, Any] | None = None,
    hours_ahead: int = DEFAULT_HOURS_AHEAD,
    hours_behind: int = DEFAULT_HOURS_BEHIND,
) -> set[str]:
    """Today + next 2 days (existing live look-ahead) plus any calendar
    kickoff dates that fall inside the live window — so a poll delayed into
    the next UTC day still queries yesterday and can recover the fixture."""
    now = _as_utc(now if now is not None else pd.Timestamp.now(tz="UTC"))
    dates = {
        now.strftime("%Y-%m-%d"),
        (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        (now + pd.Timedelta(days=2)).strftime("%Y-%m-%d"),
    }
    for rec in fixtures_in_live_window(now, payload, hours_ahead, hours_behind):
        try:
            dates.add(utc_date_str(rec["kickoff"]))
        except (KeyError, TypeError, ValueError):
            continue
    return dates


def write_upcoming_from_calendar(now: pd.Timestamp | None = None,
                                 payload: dict[str, Any] | None = None) -> list[dict]:
    return write_dashboard_upcoming(now, payload)


def write_dashboard_upcoming(now: pd.Timestamp | None = None,
                             payload: dict[str, Any] | None = None,
                             with_watchlist: bool = False) -> list[dict]:
    """What the dashboard reads: API/calendar rows first, Understat fills
    any holes (and the whole list when the API calendar is empty)."""
    now = _as_utc(now if now is not None else pd.Timestamp.now(tz="UTC"))
    upcoming = merge_upcoming(
        upcoming_from_calendar(now, payload),
        upcoming_from_understat(now),
    )
    UPCOMING_LOG.parent.mkdir(parents=True, exist_ok=True)
    UPCOMING_LOG.write_text(json.dumps(upcoming, indent=2))
    if with_watchlist:
        try:
            from . import watchlist as wl
            wl.write_watchlist(upcoming)
        except Exception as e:
            print(f"  ! watchlist write failed (upcoming list itself is fine): {e}")
    return upcoming


def refresh_calendar(client: ApiFootballClient,
                     now: pd.Timestamp | None = None,
                     horizon_days: int = HORIZON_DAYS) -> dict[str, Any]:
    """One date-only fixtures query per day in the horizon (Free-tier-safe;
    league+season combo is blocked). Filters client-side to tracked leagues."""
    now = _as_utc(now if now is not None else pd.Timestamp.now(tz="UTC"))
    api_ids = set(LEAGUE_API_IDS.values())
    all_fx: list[dict] = []
    for i in range(horizon_days + 1):
        date_str = (now + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            all_fx.extend(client.fixtures_by_date(date_str))
        except ApiFootballError as e:
            print(f"! calendar fetch failed for {date_str}: {e}")

    slim = []
    seen_ids: set = set()
    for fx in all_fx:
        try:
            if fx["league"]["id"] not in api_ids:
                continue
            fid = fx["fixture"]["id"]
        except (KeyError, TypeError):
            continue
        if fid in seen_ids:
            continue
        seen_ids.add(fid)
        slim.append({
            "fixture_id": fid,
            "league_id": fx["league"]["id"],
            "home": fx["teams"]["home"]["name"],
            "away": fx["teams"]["away"]["name"],
            "kickoff": fx["fixture"]["date"],
        })
    payload = {
        "refreshed_at": now.isoformat(),
        "horizon_days": horizon_days,
        "fixtures": slim,
    }
    save_calendar(payload)
    write_upcoming_from_calendar(now, payload)
    print(f"calendar: {len(slim)} tracked fixture(s) over {horizon_days}d "
          f"-> {CALENDAR_FILE}")
    return payload


def should_run_live_engines(now: pd.Timestamp | None = None,
                            seen: set | None = None,
                            payload: dict[str, Any] | None = None) -> bool:
    """True unless we have a fresh calendar AND every fixture currently in
    the live window is already in the seen set (already processed once
    lineups confirmed). Missing/stale calendar fails open."""
    now = _as_utc(now if now is not None else pd.Timestamp.now(tz="UTC"))
    payload = payload if payload is not None else load_calendar()
    if not calendar_is_fresh(now, payload=payload):
        print("calendar missing or stale - fail open, run live engines")
        return True
    if seen is None:
        seen = _load_seen()
    seen_norm = {int(x) if str(x).isdigit() else x for x in seen}
    unseen = []
    for rec in fixtures_in_live_window(now, payload):
        fid = rec.get("fixture_id")
        try:
            fid_n = int(fid)
        except (TypeError, ValueError):
            fid_n = fid
        if fid_n not in seen_norm and fid not in seen:
            unseen.append(rec)
    if unseen:
        print(f"calendar: {len(unseen)} unseen fixture(s) in live window "
              f"- run live engines")
        return True
    print("calendar: no unseen fixtures in live window - skip live engines")
    return False


def _write_github_output(should_run: bool) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a") as f:
        f.write(f"should_run={'true' if should_run else 'false'}\n")


def gate() -> bool:
    """Entry point for live_poll.yml: refresh a stale calendar (needs
    API_FOOTBALL_KEY), rewrite upcoming_fixtures.json from it, then decide
    whether this poll should spend quota on lineups/odds/Playwright."""
    now = pd.Timestamp.now(tz="UTC")
    if not calendar_is_fresh(now):
        try:
            refresh_calendar(ApiFootballClient(), now)
        except Exception as e:
            print(f"! calendar refresh failed ({e}); gating on whatever we have")
            n = len(write_dashboard_upcoming(now, with_watchlist=True))
            print(f"wrote {n} upcoming preview(s) from fallback sources")
    else:
        n = len(write_dashboard_upcoming(now, with_watchlist=True))
        print(f"calendar fresh - wrote {n} upcoming preview(s)")
    should = should_run_live_engines(now)
    _write_github_output(should)
    return should


if __name__ == "__main__":
    if "--gate" in sys.argv:
        ok = gate()
        print(f"should_run={ok}")
        sys.exit(0)
    if "--refresh" in sys.argv:
        refresh_calendar(ApiFootballClient())
        sys.exit(0)
    if "--from-understat" in sys.argv:
        rows = write_dashboard_upcoming(with_watchlist=True)
        print(f"upcoming_fixtures.json: {len(rows)} preview(s) from calendar+Understat")
        sys.exit(0)
    print("usage: python -m footymodel.live.calendar --gate|--refresh|--from-understat")
    sys.exit(2)
