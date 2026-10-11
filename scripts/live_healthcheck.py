"""Fail a scheduled poll when its persisted live state is no longer healthy.

GitHub Actions can finish successfully after a quiet or partially degraded
poll. This check runs after state has been committed so it surfaces stale live
output without discarding any recovery data written during that same run.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_MAX_RECOMMENDATION_AGE_HOURS = 14 * 24
DEFAULT_MAX_CALENDAR_AGE_HOURS = 48
DEFAULT_RAPIDAPI_WARNING_AT = 80
FIXTURE_FAILURE_GRACE_HOURS = 1


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _load_json(path: Path) -> dict:
    with path.open() as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object")
    return payload


def latest_recommendation_at(path: Path) -> datetime | None:
    if not path.exists():
        return None
    with path.open(newline="") as f:
        rows = csv.DictReader(f)
        timestamps = [_parse_timestamp(row["logged_at"])
                      for row in rows if row.get("logged_at")]
    return max(timestamps, default=None)


def fixture_failures(path: Path, now: datetime,
                     grace_hours: int = FIXTURE_FAILURE_GRACE_HOURS) -> list[str]:
    """Return post-kickoff fixtures whose last attempted live processing failed."""
    try:
        payload = _load_json(path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        return [f"fixture processing state is unreadable: {e}"]

    failures = []
    for record in payload.values():
        if not isinstance(record, dict) or record.get("outcome") == "processed":
            continue
        try:
            kickoff = _parse_timestamp(str(record["kickoff"]))
        except (KeyError, TypeError, ValueError):
            failures.append(f"fixture processing state has an invalid kickoff: {record}")
            continue
        if (now - kickoff).total_seconds() < grace_hours * 3600:
            continue
        fixture = f"{record.get('home', '?')} v {record.get('away', '?')}"
        outcome = record.get("outcome", "unknown failure")
        detail = record.get("detail") or "no detail recorded"
        failures.append(f"{fixture} ({record.get('fixture_id', '?')}) {outcome}: {detail}")
    return failures


def check(processed_dir: Path, now: datetime, max_recommendation_age_hours: int,
          max_calendar_age_hours: int, rapidapi_warning_at: int) -> list[str]:
    now = now.astimezone(timezone.utc)
    issues: list[str] = []

    latest = latest_recommendation_at(processed_dir / "live_recommendations.csv")
    if latest is None:
        issues.append("no live recommendation has been logged")
    elif (now - latest).total_seconds() > max_recommendation_age_hours * 3600:
        age_days = (now - latest).total_seconds() / 86400
        issues.append(f"latest live recommendation is {age_days:.1f} days old ({latest.isoformat()})")

    calendar_path = processed_dir / "fixture_calendar.json"
    try:
        calendar = _load_json(calendar_path)
        refreshed_at = _parse_timestamp(calendar["refreshed_at"])
        if (now - refreshed_at).total_seconds() > max_calendar_age_hours * 3600:
            age_hours = (now - refreshed_at).total_seconds() / 3600
            issues.append(f"fixture calendar is {age_hours:.1f} hours old ({refreshed_at.isoformat()})")
        if not calendar.get("fixtures"):
            issues.append("fixture calendar is empty")
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
        issues.append(f"fixture calendar is unreadable: {e}")

    issues.extend(fixture_failures(processed_dir / "live_fixture_health.json", now))

    budget_path = processed_dir / "rapidapi_budget.json"
    try:
        calls_used = int(_load_json(budget_path)["calls_used"])
        if calls_used >= rapidapi_warning_at:
            issues.append(f"RapidAPI budget is nearly exhausted ({calls_used}/90 calls used)")
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
        issues.append(f"RapidAPI budget state is unreadable: {e}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--max-recommendation-age-hours", type=int,
                        default=DEFAULT_MAX_RECOMMENDATION_AGE_HOURS)
    parser.add_argument("--max-calendar-age-hours", type=int,
                        default=DEFAULT_MAX_CALENDAR_AGE_HOURS)
    parser.add_argument("--rapidapi-warning-at", type=int, default=DEFAULT_RAPIDAPI_WARNING_AT)
    args = parser.parse_args()

    issues = check(args.processed_dir, datetime.now(timezone.utc),
                   args.max_recommendation_age_hours, args.max_calendar_age_hours,
                   args.rapidapi_warning_at)
    if not issues:
        print("live health check: OK")
        return 0
    print("live health check: FAILED")
    for issue in issues:
        print(f"- {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
