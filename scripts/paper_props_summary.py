#!/usr/bin/env python3
"""Print € paper props bankroll + open/settled bet counts."""
from __future__ import annotations

import csv
from pathlib import Path

from footymodel.live.paper_props_bankroll import LEDGER_PATH, STATE_PATH, load_state


def main() -> None:
    state = load_state()
    print(f"Paper props bankroll: €{state['bankroll']:.2f} (started €{state['starting_bankroll']:.2f})")
    if not LEDGER_PATH.exists():
        print("No bets placed yet.")
        return
    with LEDGER_PATH.open(newline="") as f:
        rows = list(csv.DictReader(f))
    open_n = sum(1 for r in rows if r.get("status") == "open")
    won = sum(1 for r in rows if r.get("status") == "won")
    lost = sum(1 for r in rows if r.get("status") == "lost")
    pnl = sum(float(r["pnl_eur"]) for r in rows if r.get("pnl_eur"))
    print(f"Bets: {len(rows)} total ({open_n} open, {won} won, {lost} lost); settled P&L €{pnl:.2f}")


if __name__ == "__main__":
    main()
