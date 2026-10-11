"""Pure checks for the persisted-state live pipeline health check."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.live_healthcheck import check


tmp = Path(tempfile.mkdtemp())
now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)

(tmp / "live_recommendations.csv").write_text(
    "logged_at,fixture_id\n2026-10-10T13:00:00+00:00,123\n"
)
(tmp / "fixture_calendar.json").write_text(json.dumps({
    "refreshed_at": "2026-10-10T13:00:00+00:00", "fixtures": [],
}))
(tmp / "rapidapi_budget.json").write_text(json.dumps({"calls_used": 40}))

assert check(tmp, now, 14 * 24, 48, 80) == []

(tmp / "live_recommendations.csv").write_text(
    "logged_at,fixture_id\n2026-09-01T13:00:00+00:00,123\n"
)
(tmp / "fixture_calendar.json").write_text(json.dumps({
    "refreshed_at": "2026-10-01T13:00:00+00:00", "fixtures": [],
}))
(tmp / "rapidapi_budget.json").write_text(json.dumps({"calls_used": 85}))

issues = check(tmp, now, 14 * 24, 48, 80)
assert len(issues) == 3, issues
assert any("recommendation" in issue for issue in issues)
assert any("calendar" in issue for issue in issues)
assert any("RapidAPI" in issue for issue in issues)

print("live_healthcheck_test: OK")
