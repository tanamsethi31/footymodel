"""Build the evaluations table once, then sweep O/U betting configs.

Finds the market-blend + edge-threshold config that maximizes Closing Line
Value on the Over/Under market. CLV > 0 is the gate for a genuine edge.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel import config
from footymodel.data import load, PROCESSED_DIR
from footymodel.strategy import build_evaluations, simulate

LEAGUES = config.DEFAULT_LEAGUES        # 7 main leagues (PL + mid-tier)
TEST_START = "2022-07-01"
EVALS_PATH = PROCESSED_DIR / "evals_main.parquet"

# Build (or reuse) the expensive walk-forward evaluations.
if EVALS_PATH.exists():
    evals = pd.read_parquet(EVALS_PATH)
    print(f"Loaded cached evaluations: {len(evals)} selections")
else:
    print("Building evaluations (walk-forward, per matchday)...")
    evals = build_evaluations(load(), LEAGUES, TEST_START, blend=1.0)
    evals.to_parquet(EVALS_PATH, index=False)
    print(f"Saved -> {EVALS_PATH}  ({len(evals)} selections)")

print("\n" + "=" * 78)
print("O/U-ONLY STRATEGY SWEEP  (market_blend: 1.0=pure model, lower=more market)")
print("=" * 78)
print(f"{'odds':>5} {'blend':>6} {'edge':>5} {'bets':>6} {'yield':>8} {'CLV':>8} {'beat%':>6} {'avgO':>5}")
print("-" * 78)

best = None
for bet_odds in ["close", "open"]:
    for mblend in [1.0, 0.8, 0.6]:
        for edge in [0.03, 0.05, 0.08, 0.12]:
            _, m = simulate(evals, bet_odds=bet_odds, market_blend=mblend,
                            edge=edge, markets=["over25", "under25"])
            if m["n"] == 0:
                continue
            print(f"{bet_odds:>5} {mblend:>6.1f} {edge:>5.2f} {m['n']:>6d} "
                  f"{m['yield']:>+7.2f}% {m['clv']:>+7.2f}% {m['beat']:>5.1f}% {m['avg_odds']:>5.2f}")
            # rank by CLV, require a meaningful sample
            if m["n"] >= 100 and (best is None or m["clv"] > best[1]["clv"]):
                best = ((bet_odds, mblend, edge), m)
    print("-" * 78)

if best:
    (bo, mb, ed), m = best
    print(f"\nBest O/U config by CLV: bet_odds={bo}, market_blend={mb}, edge={ed}")
    print(f"  -> {m['n']} bets, yield {m['yield']:+.2f}%, CLV {m['clv']:+.2f}%, beat-close {m['beat']:.1f}%")
