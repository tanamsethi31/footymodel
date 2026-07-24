"""Compare goals-vs-xG blends across the big-5 leagues (Phase 2b experiment).

For each blend in {1.0 goals ... 0.0 pure xG}, run the walk-forward value
backtest on every xG-covered league, then report pooled yield, bet count,
and a single calibration-error number (mean |pred-actual| over thick bins).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from footymodel.understat import load_xg, XG_LEAGUES
from footymodel.backtest import walk_forward, calibration_table

TEST_START = "2022-07-01"
EDGE = 0.05
BLENDS = [1.0, 0.5, 0.0]

df = load_xg()
rows = []
for blend in BLENDS:
    league_bets, league_preds = [], []
    per_league = {}
    for lg in XG_LEAGUES:
        bets, preds = walk_forward(df, lg, TEST_START, edge=EDGE, blend=blend)
        league_bets.append(bets)
        league_preds.append(preds)
        y = (bets["profit"].sum() / len(bets) * 100) if len(bets) else float("nan")
        per_league[lg] = (len(bets), y)
    allb = pd.concat(league_bets, ignore_index=True)
    allp = pd.concat(league_preds, ignore_index=True)
    yld = allb["profit"].sum() / len(allb) * 100
    # calibration error over bins with >=200 samples
    ct = calibration_table(allp)
    thick = ct[ct["n"] >= 200]
    cal_err = (thick["actual"] - thick["pred_mean"]).abs().mean()
    rows.append({"blend": blend, "n_bets": len(allb), "pooled_yield": yld,
                 "cal_err": cal_err, "per_league": per_league})

print("\n\n" + "=" * 70)
print(f"{'blend':>6} {'target':>14} {'bets':>6} {'pooled yield':>13} {'cal_err':>9}")
print("-" * 70)
for r in rows:
    tgt = f"goals={r['blend']:g}/xG={1-r['blend']:g}"
    print(f"{r['blend']:>6.1f} {tgt:>14} {r['n_bets']:>6d} {r['pooled_yield']:>+12.2f}% {r['cal_err']:>8.3f}")

print("\nPer-league yield (n bets):")
hdr = "  ".join(f"{lg:>10}" for lg in XG_LEAGUES)
print(f"{'blend':>6}  {hdr}")
for r in rows:
    cells = []
    for lg in XG_LEAGUES:
        n, y = r["per_league"][lg]
        cells.append(f"{y:>+6.1f}%({n})")
    print(f"{r['blend']:>6.1f}  " + "  ".join(f"{c:>10}" for c in cells))
