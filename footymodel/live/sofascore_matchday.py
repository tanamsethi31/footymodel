"""One SofaScore browser session: goals O/U then player props (home network)."""
from __future__ import annotations

import traceback

from .paper_bankroll import settle_open_bets
from .sofascore_client import SofaScoreClient
from .sofascore_engine import SofaScoreWatcher
from .sofascore_props_engine import SofaScorePropsWatcher


def run_matchday_poll() -> None:
    settle_open_bets()
    with SofaScoreClient() as client:
        SofaScoreWatcher(client).run_once()
        SofaScorePropsWatcher(client).run_once()


if __name__ == "__main__":
    print("!" * 72)
    print("MATCHDAY PAPER MODE — Goals O/U 2.5 + player shots/SOT (SofaScore).")
    print("!" * 72)
    try:
        run_matchday_poll()
    except Exception:
        print("!" * 72)
        print("MATCHDAY POLL FAILED. Traceback:")
        print("!" * 72)
        traceback.print_exc()
        raise
