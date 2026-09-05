"""Kelly-fraction bankroll Monte Carlo simulator - CLI.

Runs footymodel.simulate.sweep() over the E0 O/U 2.5 backtested value bets
and writes data/processed/kelly_simulation.csv for the dashboard's Staking
tab. Manual/periodic - only depends on evals_main.parquet (built by
scripts/ou_strategy.py or scripts/best_price.py), which only changes when
the backtest is re-run, so this isn't wired into the live poller.

Usage:
    python scripts/kelly_simulation.py
    python scripts/kelly_simulation.py --n-trials 20000 --start-bankroll 200
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.simulate import SIM_OUTPUT_PATH, load_value_bets, sweep


def main():
    parser = argparse.ArgumentParser(
        description="Kelly-fraction bankroll Monte Carlo simulator - runs sweep() over "
                     "the E0 O/U 2.5 backtested value bets and writes kelly_simulation.csv."
    )
    parser.add_argument("--n-trials", type=int, default=10_000,
                        help="simulated seasons per strategy (default: 10000)")
    parser.add_argument("--start-bankroll", type=float, default=100.0,
                        help="starting bankroll in units (default: 100.0)")
    parser.add_argument("--edge-threshold", type=float, default=0.05,
                        help="minimum edge (model_p * odds - 1) to count as a value bet (default: 0.05)")
    parser.add_argument("--seed", type=int, default=0,
                        help="rng seed, shared across all strategies for a paired comparison (default: 0)")
    args = parser.parse_args()

    bets = load_value_bets(edge_threshold=args.edge_threshold)
    print(f"Loaded {len(bets)} E0 O/U 2.5 value bets "
          f"({bets['date'].min()} to {bets['date'].max()})")

    result = sweep(bets, n_trials=args.n_trials, start_bankroll=args.start_bankroll,
                   seed=args.seed)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result.to_csv(SIM_OUTPUT_PATH, index=False)
    dashboard_copy = Path(__file__).resolve().parent.parent / "dashboard" / "data" / "kelly_simulation.csv"
    dashboard_copy.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(dashboard_copy, index=False)
    print(f"Saved -> {SIM_OUTPUT_PATH}\n")

    print(f"{'strategy':>13} {'median':>9} {'p5':>9} {'p95':>9} {'maxDD':>7} {'ruin%':>7}")
    for _, r in result.iterrows():
        print(f"{r['strategy']:>13} {r['median_final_bankroll']:>9.1f} "
              f"{r['p5_final_bankroll']:>9.1f} {r['p95_final_bankroll']:>9.1f} "
              f"{r['median_max_drawdown']*100:>6.1f}% {r['ruin_probability']*100:>6.1f}%")


if __name__ == "__main__":
    main()
