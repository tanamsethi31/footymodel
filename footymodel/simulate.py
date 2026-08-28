"""Kelly-fraction bankroll Monte Carlo simulator.

Takes the walk-forward backtest's already-proven E0 O/U 2.5 edge as given and
answers a downstream question: at what Kelly fraction is staking actually
safe, in terms of risk of ruin, drawdown, and bankroll growth? Does NOT touch
model accuracy/calibration or search for new edge - see
docs/superpowers/specs/2026-08-28-kelly-bankroll-simulation-design.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import PROCESSED_DIR
from .staking import recommended_stake

EVALS_PATH = PROCESSED_DIR / "evals_main.parquet"
SIM_OUTPUT_PATH = PROCESSED_DIR / "kelly_simulation.csv"

DEFAULT_EDGE_THRESHOLD = 0.05  # matches backtest.py / recommend.py's value-bet gate
RUIN_FLOOR_FRACTION = 0.05     # "ruined" = bankroll <= 5% of start_bankroll

# (label, kelly_mult) - kelly_mult=None means flat (fixed 1-unit) staking.
STRATEGIES = [
    ("flat", None),
    ("kelly-0.125", 0.125),
    ("kelly-0.25", 0.25),
    ("kelly-0.5", 0.5),
    ("kelly-1.0", 1.0),
]


def filter_value_bets(df: pd.DataFrame, league: str = "E0",
                       markets: tuple[str, ...] = ("over25", "under25"),
                       edge_threshold: float = DEFAULT_EDGE_THRESHOLD) -> pd.DataFrame:
    """Filter evals rows to positive-EV bets, sorted chronologically.

    `df` needs columns: date, league, market, model_p, odds_close.
    """
    sub = df[(df["league"] == league) & (df["market"].isin(markets))].copy()
    sub["edge"] = sub["model_p"] * sub["odds_close"] - 1.0
    sub = sub[sub["edge"] > edge_threshold]
    sub = sub.sort_values("date").reset_index(drop=True)
    return sub[["date", "market", "model_p", "odds_close"]]


def load_value_bets(league: str = "E0", markets: tuple[str, ...] = ("over25", "under25"),
                     edge_threshold: float = DEFAULT_EDGE_THRESHOLD) -> pd.DataFrame:
    """Read evals_main.parquet and filter to positive-EV bets. See filter_value_bets."""
    df = pd.read_parquet(EVALS_PATH)
    return filter_value_bets(df, league=league, markets=markets, edge_threshold=edge_threshold)
