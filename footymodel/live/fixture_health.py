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
