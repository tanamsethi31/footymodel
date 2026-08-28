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


def simulate_bankroll(bets: pd.DataFrame, kelly_mult: float | None,
                       n_trials: int = 10_000, start_bankroll: float = 100.0,
                       max_fraction: float = 0.02, seed: int | None = None) -> dict:
    """Run n_trials independent simulated seasons over `bets`, in the given order.

    Each trial draws its own win/loss outcome per bet from a Bernoulli(model_p)
    distribution (parametric Monte Carlo - the real historical outcome is not
    used). kelly_mult=None means flat staking: 1 unit (1% of start_bankroll)
    per bet, fixed, non-compounding, matching backtest.py's flat convention.
    Otherwise stakes via staking.recommended_stake(), unmodified.

    "Ruined" = bankroll falls to or below RUIN_FLOOR_FRACTION * start_bankroll
    (proportional Kelly staking can only asymptotically approach zero, so a
    literal bankroll<=0 definition would never trigger for Kelly strategies -
    see the design spec for the full rationale). Once ruined, a trial stops
    processing further bets (bankroll frozen at the ruin value).

    Returns {"final_bankroll": np.ndarray, "max_drawdown": np.ndarray,
             "ruined": np.ndarray[bool]}, each of shape (n_trials,).
    """
    rng = np.random.default_rng(seed)
    probs = bets["model_p"].to_numpy()
    odds = bets["odds_close"].to_numpy()
    n_bets = len(probs)
    ruin_floor = start_bankroll * RUIN_FLOOR_FRACTION
    flat_stake = start_bankroll * 0.01

    final_bankroll = np.empty(n_trials)
    max_drawdown = np.empty(n_trials)
    ruined = np.zeros(n_trials, dtype=bool)

    for t in range(n_trials):
        bankroll = start_bankroll
        peak = start_bankroll
        worst_dd = 0.0
        outcomes = rng.random(n_bets) < probs

        for i in range(n_bets):
            if bankroll <= ruin_floor:
                ruined[t] = True
                break

            if kelly_mult is None:
                stake = min(flat_stake, bankroll)
            else:
                stake = recommended_stake(bankroll, probs[i], odds[i],
                                          kelly_mult=kelly_mult, max_fraction=max_fraction)
            if stake <= 0:
                continue

            if outcomes[i]:
                bankroll += stake * (odds[i] - 1.0)
            else:
                bankroll -= stake

            peak = max(peak, bankroll)
            if peak > 0:
                worst_dd = max(worst_dd, (peak - bankroll) / peak)

        final_bankroll[t] = max(bankroll, 0.0)
        max_drawdown[t] = worst_dd

    return {"final_bankroll": final_bankroll, "max_drawdown": max_drawdown, "ruined": ruined}
