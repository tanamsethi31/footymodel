#!/usr/bin/env python3
"""Settle open € paper player-prop bets using graded_props_players.csv."""
from __future__ import annotations

from footymodel.live.paper_bankroll import settle_open_bets


def main() -> None:
    n = settle_open_bets()
    if n == 0:
        print("No open paper props bets were settled this run.")


if __name__ == "__main__":
    main()
