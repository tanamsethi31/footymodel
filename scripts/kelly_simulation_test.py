"""Unit-checks for the Kelly bankroll Monte Carlo simulator
(footymodel/simulate.py). Pure/data-free - builds tiny synthetic bet sets
inline, never reads evals_main.parquet - safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.simulate import filter_value_bets

# --- filter_value_bets -------------------------------------------------
raw = pd.DataFrame([
    # league, market, model_p, odds_close -> edge = p*odds-1
    {"date": "2024-01-03", "league": "E0", "market": "over25", "model_p": 0.60, "odds_close": 2.00},  # edge=0.20, KEEP
    {"date": "2024-01-01", "league": "E0", "market": "under25", "model_p": 0.55, "odds_close": 1.90},  # edge=0.045, DROP (below 0.05 threshold)
    {"date": "2024-01-02", "league": "E0", "market": "home", "model_p": 0.70, "odds_close": 2.00},     # edge=0.40, DROP (wrong market)
    {"date": "2024-01-04", "league": "D1", "market": "over25", "model_p": 0.70, "odds_close": 2.00},   # edge=0.40, DROP (wrong league)
])

result = filter_value_bets(raw, league="E0", markets=("over25", "under25"), edge_threshold=0.05)
assert len(result) == 1, f"expected 1 value bet, got {len(result)}"
assert result.iloc[0]["market"] == "over25"
assert list(result.columns) == ["date", "market", "model_p", "odds_close"]

# Chronological sort check - dates in the raw frame are out of order.
raw2 = pd.DataFrame([
    {"date": "2024-03-01", "league": "E0", "market": "over25", "model_p": 0.60, "odds_close": 2.00},
    {"date": "2024-01-01", "league": "E0", "market": "over25", "model_p": 0.60, "odds_close": 2.00},
    {"date": "2024-02-01", "league": "E0", "market": "over25", "model_p": 0.60, "odds_close": 2.00},
])
sorted_result = filter_value_bets(raw2, league="E0", edge_threshold=0.05)
assert list(sorted_result["date"]) == ["2024-01-01", "2024-02-01", "2024-03-01"]

print("kelly_simulation_test: filter_value_bets OK")
