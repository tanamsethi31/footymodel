"""Pure checks for the persisted-state live pipeline health check."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.live_healthcheck import check, fixture_failures


tmp = Path(tempfile.mkdtemp())
now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)

(tmp / "live_recommendations.csv").write_text(
    "logged_at,fixture_id\n2026-10-10T13:00:00+00:00,123\n"
)
(tmp / "fixture_calendar.json").write_text(json.dumps({
    "refreshed_at": "2026-10-10T13:00:00+00:00", "fixtures": [{"fixture_id": "123"}],
}))
(tmp / "rapidapi_budget.json").write_text(json.dumps({"calls_used": 40}))
(tmp / "live_fixture_health.json").write_text(json.dumps({
    "123": {
        "fixture_id": "123", "kickoff": "2026-10-11T11:30:00+00:00",
        "home": "Arsenal", "away": "Chelsea", "outcome": "processed",
    }
}))

assert check(tmp, now, 14 * 24, 48, 80) == []

(tmp / "live_recommendations.csv").write_text(
    "logged_at,fixture_id\n2026-09-01T13:00:00+00:00,123\n"
)
(tmp / "fixture_calendar.json").write_text(json.dumps({
    "refreshed_at": "2026-10-01T13:00:00+00:00", "fixtures": [],
}))
(tmp / "rapidapi_budget.json").write_text(json.dumps({"calls_used": 85}))
(tmp / "live_fixture_health.json").write_text(json.dumps({
    "123": {
        "fixture_id": "123", "kickoff": "2026-10-11T09:00:00+00:00",
        "home": "Arsenal", "away": "Chelsea", "outcome": "odds_unavailable",
        "detail": "lineup available but no usable O/U odds",
    },
    "124": {
        "fixture_id": "124", "kickoff": "2026-10-11T11:30:00+00:00",
        "home": "Everton", "away": "Liverpool", "outcome": "lineup_unavailable",
        "detail": "still inside the grace period",
    },
}))

issues = check(tmp, now, 14 * 24, 48, 80)
assert len(issues) == 5, issues
assert any("recommendation" in issue for issue in issues)
assert any("calendar" in issue for issue in issues)
assert any("RapidAPI" in issue for issue in issues)
assert any("odds_unavailable" in issue for issue in issues)
assert not any("Everton v Liverpool" in issue for issue in issues)

(tmp / "live_fixture_health.json").unlink()
assert fixture_failures(tmp / "live_fixture_health.json", now) == []

(tmp / "live_fixture_health.json").write_text("not json")
assert fixture_failures(tmp / "live_fixture_health.json", now)[0].startswith(
    "fixture processing state is unreadable"
)

print("live_healthcheck_test: OK")
