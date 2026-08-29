"""Unit-check for grade_results.py's ragged-column parsing. The three live
engines log a different number of trailing fields depending on whether they
write a "source" field (engine.py never does; rapidapi_engine.py and
sofascore_engine.py always do) and whether odds were available at the time
(fair_p_over25/ev_over25/ev_under25 are all-or-nothing together). A fixed
pd.read_csv(names=<16 columns>) silently mis-shifted any row that wasn't
exactly 16 fields wide - confirmed live, 2026-08-28: the first engine.py
row that ever got real odds (Crystal Palace v Manchester City) had its
ev_over25 read as ev_under25's real value, with ev_under25 itself coming
back blank, so a real +7.3% EV bet was silently never placed. Pure/data-free
- safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.grade_results import parse_prediction_row

# 0 extra fields (engine.py, no odds yet).
base = [
    "2026-08-23T13:00:00", "1557370", "E0", "2026-08-23T13:00:00+00:00",
    "Brighton", "Aston Villa", "10", "10", "0.442", "2.44",
]
row = parse_prediction_row(base + ["", ""])
assert "source" not in row
assert "ev_over25" not in row

# 3 extra fields (engine.py, with odds - the exact case that was broken).
row = parse_prediction_row(base + ["1.77", "2.26", "0.561", "0.073", "-0.111"])
assert "source" not in row
assert row["fair_p_over25"] == 0.561
assert row["ev_over25"] == 0.073
assert row["ev_under25"] == -0.111

# 1 extra field (rapidapi/sofascore, no odds yet - source only).
row = parse_prediction_row(base + ["", "", "rapidapi"])
assert row["source"] == "rapidapi"
assert "ev_over25" not in row

# 4 extra fields (rapidapi/sofascore, with odds).
row = parse_prediction_row(base + ["2.20", "1.60", "rapidapi", "0.421", "0.009", "-0.134"])
assert row["source"] == "rapidapi"
assert row["fair_p_over25"] == 0.421
assert row["ev_over25"] == 0.009
assert row["ev_under25"] == -0.134

print("grade_results_columns_test: OK")
