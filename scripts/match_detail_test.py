"""Unit-check for match_detail.py's shared JSONL detail-log helpers, used by
all three live engines (engine.py/rapidapi_engine.py/sofascore_engine.py) to
log starting-XI names and the team-model/lineup-model breakdown that
live_recommendations.csv doesn't carry - see
docs/superpowers/specs/2026-08-29-expandable-match-detail-design.md. Pure/
data-free except for one temp-file write - safe to run in CI.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live import match_detail

# make_detail() shapes one match's detail row from a LineupModel.predict()
# result - the same schema regardless of which engine calls it.
pred = {
    "exp_team": 2.912, "exp_full": 3.204, "exp_blend": 3.058,
    "p_over25_team": 0.583, "p_over25_full": 0.631, "p_over25_blend": 0.606,
}
detail = match_detail.make_detail(1557370, ["Ederson", "Walker"], ["Henderson", "Munoz"], pred)
assert detail == {
    "fixture_id": 1557370,
    "home_starters": ["Ederson", "Walker"],
    "away_starters": ["Henderson", "Munoz"],
    "exp_team": 2.91, "exp_full": 3.2,
    "p_over25_team": 0.583, "p_over25_full": 0.631,
}, detail

# extract_and_log_details() pops "_detail" from each row IN PLACE (so it
# never leaks into the live_recommendations.csv DataFrame) and appends the
# collected details to MATCH_DETAIL_LOG as JSONL.
with tempfile.TemporaryDirectory() as tmp:
    match_detail.MATCH_DETAIL_LOG = Path(tmp) / "match_detail.jsonl"

    rows = [
        {"fixture_id": 1, "home": "A", "_detail": {"fixture_id": 1, "home_starters": ["X"]}},
        {"fixture_id": 2, "home": "B"},  # no "_detail" - e.g. odds fetch failed upstream
    ]
    match_detail.extract_and_log_details(rows)

    assert "_detail" not in rows[0], "detail key must be popped, never left on the CSV row"
    assert rows[0] == {"fixture_id": 1, "home": "A"}
    assert rows[1] == {"fixture_id": 2, "home": "B"}

    lines = match_detail.MATCH_DETAIL_LOG.read_text().strip().splitlines()
    assert len(lines) == 1, "only the row that HAD a _detail should be logged"
    assert json.loads(lines[0]) == {"fixture_id": 1, "home_starters": ["X"]}

    # Never raises, even when every row lacks "_detail" - it's called
    # unconditionally after every poll, confirmed-lineup or not.
    match_detail.extract_and_log_details([{"fixture_id": 3}])

print("match_detail_test: OK")
