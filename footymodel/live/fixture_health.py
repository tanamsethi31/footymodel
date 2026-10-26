"""Persist the latest live-processing outcome for each expected fixture."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..data import PROCESSED_DIR

STATE_FILE = PROCESSED_DIR / "live_fixture_health.json"


def record(fixture_id: str | int, *, kickoff: str, home: str, away: str,
           source: str, outcome: str, detail: str = "",
           checked_at: datetime | None = None) -> None:
    """Store the newest outcome, replacing any earlier poll for this fixture."""
    state: dict[str, dict] = {}
    if STATE_FILE.exists():
        try:
            payload = json.loads(STATE_FILE.read_text())
            if isinstance(payload, dict):
                state = payload
        except (json.JSONDecodeError, OSError):
            pass

    checked_at = checked_at or datetime.now(timezone.utc)
    state[str(fixture_id)] = {
        "fixture_id": str(fixture_id),
        "kickoff": kickoff,
        "home": home,
        "away": away,
        "source": source,
        "outcome": outcome,
        "detail": detail,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def load_all() -> dict[str, dict]:
    if not STATE_FILE.exists():
        return {}
    try:
        payload = json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


_SUCCESS_OUTCOMES = frozenset({"processed", "processed_model_only", "odds_unavailable"})


def calendar_row_processed(rec: dict, *, source: str = "sofascore") -> bool:
    """True if a live engine already logged this calendar fixture (home/away/kickoff day)."""
    from .calendar import match_key

    target = match_key(rec)
    for entry in load_all().values():
        if not isinstance(entry, dict):
            continue
        if source and entry.get("source") != source:
            continue
        if entry.get("outcome") not in _SUCCESS_OUTCOMES:
            continue
        try:
            if match_key(entry) == target:
                return True
        except (KeyError, TypeError):
            continue
    return False
