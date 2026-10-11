"""Pure checks for latest-outcome persistence per live fixture."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live import fixture_health


tmp = Path(tempfile.mkdtemp())
fixture_health.STATE_FILE = tmp / "live_fixture_health.json"

fixture_health.record(
    123, kickoff="2026-10-11T11:30:00+00:00", home="Arsenal", away="Chelsea",
    source="api-football", outcome="lineup_unavailable", detail="not posted yet",
    checked_at=datetime(2026, 10, 11, 11, tzinfo=timezone.utc),
)
fixture_health.record(
    123, kickoff="2026-10-11T11:30:00+00:00", home="Arsenal", away="Chelsea",
    source="api-football", outcome="processed", detail="confirmed lineup and odds",
    checked_at=datetime(2026, 10, 11, 11, 30, tzinfo=timezone.utc),
)

state = json.loads(fixture_health.STATE_FILE.read_text())
assert list(state) == ["123"]
assert state["123"]["outcome"] == "processed"
assert state["123"]["checked_at"] == "2026-10-11T11:30:00+00:00"

print("fixture_health_test: OK")
