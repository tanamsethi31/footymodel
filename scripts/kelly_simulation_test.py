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

# --- simulate_bankroll ---------------------------------------------------
from footymodel.simulate import simulate_bankroll
from footymodel.staking import recommended_stake

# Integration check: the simulator's kelly staking must match staking.py's
# recommended_stake() exactly, not a reimplementation, on a single bet.
one_bet = pd.DataFrame([
    {"date": "2024-01-01", "market": "over25", "model_p": 0.55, "odds_close": 2.00},
])
result = simulate_bankroll(one_bet, kelly_mult=0.25, n_trials=1, start_bankroll=100.0,
                           max_fraction=0.02, seed=42)
expected_stake = recommended_stake(100.0, 0.55, 2.00, kelly_mult=0.25, max_fraction=0.02)
# With a single bet, final_bankroll is start_bankroll +/- the stake's payout/loss -
# reconstruct which happened and confirm it matches the direct staking.py call.
final = result["final_bankroll"][0]
win_final = 100.0 + expected_stake * (2.00 - 1.0)
lose_final = 100.0 - expected_stake
assert abs(final - win_final) < 1e-9 or abs(final - lose_final) < 1e-9, (
    f"final_bankroll {final} doesn't match either win ({win_final}) or lose ({lose_final}) "
    f"outcome using staking.py's own stake size {expected_stake}"
)

# Ruin floor: flat staking on an all-losses bet set must ruin every trial
# (bankroll walked all the way down through the 5%-of-start floor). Flat
# staking is 1 unit = 1% of start_bankroll per bet (non-compounding), so
# crossing the 5%-of-start floor from a 100.0 start takes 95 straight losses -
# use 120 guaranteed-loss bets for comfortable margin past that threshold.
losing_bets = pd.DataFrame([
    {"date": f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}", "market": "over25",
     "model_p": 0.0, "odds_close": 2.00}
    for i in range(120)
])
result = simulate_bankroll(losing_bets, kelly_mult=None, n_trials=50, start_bankroll=100.0, seed=1)
assert result["ruined"].all(), "flat staking on 120 guaranteed losses should always ruin"
assert (result["final_bankroll"] <= 5.0).all(), "ruined trials should be at/below the 5% floor"

# Guaranteed wins never ruin, for either strategy.
winning_bets = pd.DataFrame([
    {"date": f"2024-01-{i:02d}", "market": "over25", "model_p": 1.0, "odds_close": 2.00}
    for i in range(1, 11)
])
flat_result = simulate_bankroll(winning_bets, kelly_mult=None, n_trials=20, start_bankroll=100.0, seed=2)
kelly_result = simulate_bankroll(winning_bets, kelly_mult=1.0, n_trials=20, start_bankroll=100.0, seed=2)
assert not flat_result["ruined"].any()
assert not kelly_result["ruined"].any()
assert (flat_result["final_bankroll"] > 100.0).all()
assert (kelly_result["final_bankroll"] > 100.0).all()

# Higher kelly_mult -> higher variance, on a repeated positive-edge bet with
# a thin enough edge that neither multiplier hits the max_fraction cap
# (p=0.55, odds=2.0 -> edge=0.10, full-Kelly fraction=0.10 - use a generous
# max_fraction=0.5 so both 1/8 and full Kelly stay uncapped and distinguishable).
# 300 repeats (not 60): full Kelly's proportional 10%-of-bankroll stake needs
# enough bets for its downside path to have a realistic shot at crossing the
# fixed 5%-of-start ruin floor at all - at 60 bets neither mult ever ruins
# across 3000 trials, so the ruin-rate comparison below has nothing to compare.
repeated_bets = pd.DataFrame([
    {"date": f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}", "market": "over25",
     "model_p": 0.55, "odds_close": 2.00}
    for i in range(300)
])
low_mult = simulate_bankroll(repeated_bets, kelly_mult=0.125, n_trials=3000,
                             start_bankroll=100.0, max_fraction=0.5, seed=7)
high_mult = simulate_bankroll(repeated_bets, kelly_mult=1.0, n_trials=3000,
                              start_bankroll=100.0, max_fraction=0.5, seed=7)
assert high_mult["final_bankroll"].std() > low_mult["final_bankroll"].std(), (
    "full Kelly should show higher bankroll variance than 1/8 Kelly on identical bets"
)
assert high_mult["ruined"].mean() > low_mult["ruined"].mean(), (
    "full Kelly should ruin more often than 1/8 Kelly on identical bets"
)

print("kelly_simulation_test: simulate_bankroll OK")
