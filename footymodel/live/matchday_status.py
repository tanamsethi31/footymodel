"""Shared match-day readiness: integration checks and cloud nudge logic."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..data import PROCESSED_DIR
from .calendar import calendar_is_fresh, load_calendar, should_run_live_engines
from .fixture_health import calendar_row_processed

# Typical confirmed-lineup window (minutes before kickoff).
NUDGE_MINUTES_BEFORE_KO = 15
NUDGE_MINUTES_BEFORE_KO_MAX = 180

PROPS_LOG = PROCESSED_DIR / "live_player_props.csv"
GOALS_LOG = PROCESSED_DIR / "live_recommendations.csv"
BANKROLL_STATE = PROCESSED_DIR / "paper_props_bankroll.json"
BANKROLL_LEDGER = PROCESSED_DIR / "paper_bankroll_bets.csv"
MATCHES_PARQUET = PROCESSED_DIR / "matches.parquet"


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return pd.Timestamp(value).to_pydatetime().astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def latest_csv_timestamp(path: Path, *columns: str) -> datetime | None:
    if not path.exists():
        return None
    latest: datetime | None = None
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            for col in columns:
                ts = _parse_ts(row.get(col) or "")
                if ts and (latest is None or ts > latest):
                    latest = ts
    return latest


def fixture_logged_on_sofascore(rec: dict) -> bool:
    return calendar_row_processed(rec, source="sofascore")


def fixtures_in_lineup_nudge_window(
    now: pd.Timestamp | None = None,
    payload: dict | None = None,
) -> list[dict]:
    """Calendar fixtures in the pre-kickoff window where a home poll is expected."""
    now = pd.Timestamp(now or pd.Timestamp.now(tz="UTC"))
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    else:
        now = now.tz_convert("UTC")
    payload = payload or load_calendar() or {}
    fixtures = payload.get("fixtures") or []
    out: list[dict] = []
    for rec in fixtures:
        kickoff = rec.get("kickoff")
        if not kickoff:
            continue
        try:
            ko = pd.Timestamp(kickoff)
            if ko.tzinfo is None:
                ko = ko.tz_localize("UTC")
            else:
                ko = ko.tz_convert("UTC")
        except (TypeError, ValueError):
            continue
        mins = (ko - now).total_seconds() / 60
        if not (NUDGE_MINUTES_BEFORE_KO <= mins <= NUDGE_MINUTES_BEFORE_KO_MAX):
            continue
        if fixture_logged_on_sofascore(rec):
            continue
        out.append(rec)
    return out


def needs_home_sofascore_poll(now: pd.Timestamp | None = None) -> bool:
    return len(fixtures_in_lineup_nudge_window(now)) > 0


def build_nudge_body(fixtures: list[dict]) -> str:
    lines = [f"{rec.get('home', '?')} v {rec.get('away', '?')}" for rec in fixtures[:3]]
    extra = len(fixtures) - len(lines)
    body = "Lineups due — run home poll: ./scripts/matchday_laptop.sh loop 900 --push"
    if lines:
        body += " | " + ", ".join(lines)
    if extra > 0:
        body += f" (+{extra} more)"
    return body


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    critical: bool = True


@dataclass
class MatchdayReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks if c.critical)

    def add(self, name: str, ok: bool, detail: str, *, critical: bool = True) -> None:
        self.checks.append(CheckResult(name, ok, detail, critical=critical))


def run_integration_checks(processed_dir: Path = PROCESSED_DIR) -> MatchdayReport:
    report = MatchdayReport()
    now = pd.Timestamp.now(tz="UTC")

    cal_path = processed_dir / "fixture_calendar.json"
    payload = None
    if cal_path.exists():
        try:
            payload = json.loads(cal_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            report.add("calendar", False, f"unreadable: {e}")
        else:
            fresh = calendar_is_fresh(now, payload=payload)
            n = len((payload or {}).get("fixtures") or [])
            report.add(
                "calendar",
                fresh and n > 0,
                f"{'fresh' if fresh else 'stale/missing refreshed_at'}, {n} fixture(s)",
            )
    else:
        report.add("calendar", False, f"missing {cal_path}")

    props_log = processed_dir / PROPS_LOG.name
    goals_log = processed_dir / GOALS_LOG.name
    props_at = latest_csv_timestamp(props_log, "logged_at", "kickoff")
    goals_at = latest_csv_timestamp(goals_log, "logged_at", "kickoff")
    report.add(
        "live_player_props.csv",
        props_log.exists(),
        f"latest row {props_at.isoformat() if props_at else 'never'}",
    )
    report.add(
        "live_recommendations.csv",
        goals_log.exists(),
        f"latest row {goals_at.isoformat() if goals_at else 'never'}",
    )

    state_path = processed_dir / BANKROLL_STATE.name
    ledger_path = processed_dir / BANKROLL_LEDGER.name
    legacy_ledger = processed_dir / "paper_props_bets.csv"
    report.add(
        "paper bankroll state",
        state_path.exists(),
        "present" if state_path.exists() else f"missing {state_path.name}",
    )
    has_ledger = ledger_path.exists() or legacy_ledger.exists()
    report.add(
        "paper bankroll ledger",
        has_ledger,
        "present"
        if has_ledger
        else "missing until first matchday poll places bets",
        critical=False,
    )

    mp = processed_dir / MATCHES_PARQUET.name
    report.add(
        "matches.parquet (goals grading)",
        mp.exists(),
        "present" if mp.exists() else "missing — grade_results refreshes E0 in CI",
    )

    graded_props = processed_dir / "graded_props_players.csv"
    graded_goals = processed_dir / "graded_results.csv"
    report.add(
        "graded_props_players.csv",
        graded_props.exists(),
        "present" if graded_props.exists() else "optional until first props grade",
        critical=False,
    )
    report.add(
        "graded_results.csv",
        graded_goals.exists(),
        "present" if graded_goals.exists() else "optional until first goals grade",
        critical=False,
    )

    gate = should_run_live_engines(now, payload=payload)
    nudge = needs_home_sofascore_poll(now)
    report.add(
        "calendar_gate",
        True,
        f"should_run_live_engines={gate}",
    )
    report.add(
        "home_poll_nudge",
        not nudge,
        f"{len(fixtures_in_lineup_nudge_window(now, payload))} fixture(s) need SofaScore on home IP"
        if nudge
        else "no fixtures in lineup window without a SofaScore log",
        critical=False,
    )

    return report
