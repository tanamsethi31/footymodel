"""Phase 5 — staking / bankroll rules.

Fractional Kelly with hard caps. Kelly maximizes long-run growth *when you have a
real edge*; with no proven edge it just sizes losses, so we default to a small
fraction and a low cap, and never stake without a positive modelled edge.

For a bet with win probability p at decimal odds o:
    full Kelly fraction f* = (p*o - 1) / (o - 1)          (= edge / (o - 1))
We stake  kelly_mult * f*  of bankroll, capped at max_fraction.
"""
from __future__ import annotations


def kelly_fraction(p: float, odds: float) -> float:
    """Full-Kelly fraction of bankroll. Non-positive when there's no edge."""
    if odds <= 1.0:
        return 0.0
    return (p * odds - 1.0) / (odds - 1.0)


def recommended_stake(bankroll: float, p: float, odds: float,
                      kelly_mult: float = 0.25, max_fraction: float = 0.02,
                      min_stake: float = 0.0) -> float:
    """Stake in bankroll units. 1/4 Kelly by default, capped at 2% of bankroll.

    Returns 0 when there is no positive edge (never chase)."""
    f = kelly_fraction(p, odds)
    if f <= 0:
        return 0.0
    frac = min(kelly_mult * f, max_fraction)
    stake = bankroll * frac
    return stake if stake >= min_stake else 0.0
