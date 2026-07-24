"""Phase 6 — the betting recommender (weekly bet-slip generator).

Fits the Dixon-Coles model on all available history for a league and produces
Over/Under value recommendations for upcoming fixtures, with fractional-Kelly
stakes. Every run appends to a paper-trade log so live performance can be
tracked against the backtest before any real money is risked.

    HONEST STATUS: the backtest shows NO positive edge (O/U yield ~-7%, CLV
    ~-0.2%). This tool ships in PAPER-TRADE mode. Do not stake real money unless
    live paper results turn positive, or you add an information edge the market
    lacks (injuries/lineups/news).

Usage:
    python -m footymodel.recommend --league E1                 # demo on latest matchday
    python -m footymodel.recommend --league E1 --fixtures my_fixtures.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .data import load, PROCESSED_DIR
from .model import DixonColes
from .staking import recommended_stake, kelly_fraction
from .strategy import remove_margin

PAPER_LOG = PROCESSED_DIR / "paper_trades.csv"

# Default betting config = least-bad from the Phase 4 sweep.
DEFAULT_EDGE = 0.05
DEFAULT_MARKET_BLEND = 1.0
OU_MARKETS = [
    ("over25", "p_over25", "odds_over25"),
    ("under25", "p_under25", "odds_under25"),
]


def recommend_for_fixtures(model: DixonColes, fixtures: pd.DataFrame,
                           edge: float = DEFAULT_EDGE,
                           market_blend: float = DEFAULT_MARKET_BLEND,
                           bankroll: float = 100.0, kelly_mult: float = 0.25,
                           max_fraction: float = 0.02) -> pd.DataFrame:
    """Generate O/U value bets for `fixtures` (needs home_team, away_team,
    odds_over25, odds_under25)."""
    recs = []
    for r in fixtures.itertuples(index=False):
        if r.home_team not in model.attack or r.away_team not in model.attack:
            continue
        mp = model.predict_markets(r.home_team, r.away_team)
        o_over, o_under = getattr(r, "odds_over25", np.nan), getattr(r, "odds_under25", np.nan)
        if pd.isna(o_over) or pd.isna(o_under):
            continue
        fair = remove_margin(np.array([o_over, o_under], dtype=float))
        fair_map = {"over25": fair[0], "under25": fair[1]}
        for market, pkey, ocol in OU_MARKETS:
            odds = getattr(r, ocol)
            p_model = mp[pkey]
            p_used = market_blend * p_model + (1 - market_blend) * fair_map[market]
            ev = p_used * odds - 1.0
            if ev > edge:
                stake = recommended_stake(bankroll, p_used, odds,
                                          kelly_mult=kelly_mult, max_fraction=max_fraction)
                recs.append({
                    "date": getattr(r, "date", pd.NaT),
                    "league": getattr(r, "league", model_league(model)),
                    "home": r.home_team, "away": r.away_team,
                    "market": market, "odds": round(float(odds), 2),
                    "model_p": round(p_used, 3), "fair_p": round(fair_map[market], 3),
                    "edge_ev": round(ev, 3),
                    "kelly_full": round(kelly_fraction(p_used, odds), 3),
                    "stake": round(stake, 2),
                })
    return pd.DataFrame(recs)


def model_league(model: DixonColes) -> str:
    return getattr(model, "_league", "")


def fit_league(df: pd.DataFrame, league: str, before=None, xi: float = 0.0018,
               blend: float = 1.0) -> DixonColes:
    sub = df[df["league"] == league]
    if before is not None:
        sub = sub[sub["date"] < pd.Timestamp(before)]
    m = DixonColes(xi=xi).fit(sub, blend=blend)
    m._league = league
    return m


def log_paper_trades(slip: pd.DataFrame, path: Path = PAPER_LOG) -> None:
    if slip.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    header = not path.exists()
    slip.to_csv(path, mode="a", header=header, index=False)
    print(f"Logged {len(slip)} recommendations -> {path}")


def _banner():
    print("!" * 72)
    print("PAPER-TRADE MODE. Best-price backtest yield ~-2.6% (best case, idealized).")
    print("Enter the BEST odds you can find across bookmakers. Do NOT stake real")
    print("money unless live paper results turn positive.")
    print("!" * 72)


def demo(league: str, edge: float, market_blend: float, bankroll: float) -> None:
    """Demonstrate end-to-end on the most recent matchday in the dataset:
    fit on everything before it, recommend, then show what actually happened."""
    df = load()
    lg = df[df["league"] == league].sort_values("date")
    if lg.empty:
        print(f"No data for league {league}."); return
    last_date = lg["date"].max()
    upcoming = lg[lg["date"] == last_date].copy()
    # Bank the best-price edge: bet the market MAXIMUM odds, not the average.
    for m in ("over25", "under25"):
        if f"odds_{m}_max" in upcoming:
            upcoming[f"odds_{m}"] = upcoming[f"odds_{m}_max"]
    model = fit_league(df, league, before=last_date, blend=1.0)

    print(f"\nLeague {league} — treating {last_date.date()} as 'upcoming' "
          f"({len(upcoming)} fixtures). Model fit on {model.n_matches} prior matches.\n")
    slip = recommend_for_fixtures(model, upcoming, edge=edge,
                                  market_blend=market_blend, bankroll=bankroll)
    if slip.empty:
        print("No value bets found for this matchday at the current edge threshold.")
        return

    # Grade against actual results (demo only — normally unknown at bet time).
    res = {(r.home_team, r.away_team): (r.fthg + r.ftag)
           for r in upcoming.itertuples(index=False)}
    graded = []
    for r in slip.itertuples(index=False):
        tot = res.get((r.home, r.away))
        won = (tot > 2.5) if r.market == "over25" else (tot < 2.5)
        pnl = r.stake * (r.odds - 1) if won else -r.stake
        graded.append({"result_goals": tot, "won": won, "pnl": round(pnl, 2)})
    slip = pd.concat([slip.reset_index(drop=True), pd.DataFrame(graded)], axis=1)

    _banner()
    print(slip.to_string(index=False))
    print(f"\nDemo P&L this matchday: {slip['pnl'].sum():+.2f} u on "
          f"{slip['stake'].sum():.2f} u staked ({len(slip)} bets).")
    log_paper_trades(slip.drop(columns=["result_goals", "won", "pnl"]))


def main():
    p = argparse.ArgumentParser(description="O/U betting recommender (paper-trade).")
    p.add_argument("--league", default="E1", help="Division code (default E1 Championship)")
    p.add_argument("--fixtures", help="CSV with home_team,away_team,odds_over25,odds_under25")
    p.add_argument("--edge", type=float, default=DEFAULT_EDGE)
    p.add_argument("--market-blend", type=float, default=DEFAULT_MARKET_BLEND)
    p.add_argument("--bankroll", type=float, default=100.0)
    args = p.parse_args()

    if args.fixtures:
        df = load()
        model = fit_league(df, args.league, blend=1.0)
        fixtures = pd.read_csv(args.fixtures)
        _banner()
        slip = recommend_for_fixtures(model, fixtures, edge=args.edge,
                                      market_blend=args.market_blend, bankroll=args.bankroll)
        print(slip.to_string(index=False) if not slip.empty else "No value bets found.")
        log_paper_trades(slip)
    else:
        demo(args.league, args.edge, args.market_blend, args.bankroll)


if __name__ == "__main__":
    main()
