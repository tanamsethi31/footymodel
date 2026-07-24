"""Phase 4 — O/U-specialised, market-aware betting strategy.

Two-stage design so we can search betting configs cheaply:

  evaluate_*  — the expensive walk-forward. Fit Dixon-Coles once per matchday
                (no lookahead) and emit one row per (fixture, market) with the
                model probability, the actual outcome, and BOTH opening and
                closing odds + margin-removed "fair" market probabilities.
                Saved to data/processed/evals*.parquet.

  simulate    — cheap. Given the evaluations table, apply a betting config
                (market filter, opening/closing odds, model-market blend, edge
                threshold) and return bets + metrics (yield, CLV). Sweep freely.

Model-market blend is the key lever: our raw model is over-confident exactly
where it disagrees with the market (negative CLV). Blending our probability
toward the market's fair probability, then betting only when an edge survives,
makes us far more selective and should lift CLV.

    p_used = w * p_model + (1 - w) * p_market_fair      (w = market_blend)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .backtest import MARKETS, remove_margin
from .model import DixonColes

# Market groups share a margin-removal normalization.
GROUPS = {
    "1x2": ["home", "draw", "away"],
    "ou": ["over25", "under25"],
}
_MARKET_GROUP = {m: g for g, ms in GROUPS.items() for m in ms}


def _fair_probs(odds_by_market: dict[str, float]) -> dict[str, float]:
    """Margin-removed fair prob per selection, normalized within its group."""
    fair = {}
    for g, members in GROUPS.items():
        vals = [odds_by_market.get(m) for m in members]
        if any(v is None or pd.isna(v) for v in vals):
            for m in members:
                fair[m] = np.nan
            continue
        p = remove_margin(np.array(vals, dtype=float))
        for m, pv in zip(members, p):
            fair[m] = float(pv)
    return fair


def evaluate_league(df: pd.DataFrame, league: str, test_start: str,
                    xi: float = 0.0018, blend: float = 1.0,
                    min_train: int = 200) -> pd.DataFrame:
    """Walk-forward evaluation: one row per (fixture, market) with model prob,
    outcome, and opening/closing odds + fair probs."""
    league_df = df[df["league"] == league].sort_values("date").reset_index(drop=True)
    test_start = pd.Timestamp(test_start)
    dates = sorted(league_df.loc[league_df["date"] >= test_start, "date"].unique())

    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        train = league_df[league_df["date"] < d]
        if len(train) < min_train:
            continue
        model = DixonColes(xi=xi).fit(train, ref_date=d, blend=blend)
        for r in league_df[league_df["date"] == d].itertuples(index=False):
            if r.home_team not in model.attack or r.away_team not in model.attack:
                continue
            mp = model.predict_markets(r.home_team, r.away_team)
            close_by_m = {m: getattr(r, ocol) for m, (_, ocol, _) in MARKETS.items()}
            open_by_m = {m: getattr(r, ocol + "_open") for m, (_, ocol, _) in MARKETS.items()}
            fair_close = _fair_probs(close_by_m)
            fair_open = _fair_probs(open_by_m)
            for market, (pkey, ocol, outcome_fn) in MARKETS.items():
                rows.append({
                    "date": d, "league": league, "market": market,
                    "home": r.home_team, "away": r.away_team,
                    "model_p": mp[pkey], "won": bool(outcome_fn(r)),
                    "odds_open": open_by_m[market], "odds_close": close_by_m[market],
                    "fair_open": fair_open[market], "fair_close": fair_close[market],
                })
    return pd.DataFrame(rows)


def build_evaluations(df: pd.DataFrame, leagues: list[str], test_start: str,
                      xi: float = 0.0018, blend: float = 1.0) -> pd.DataFrame:
    frames = []
    for lg in leagues:
        print(f"  evaluating {lg} ...", flush=True)
        e = evaluate_league(df, lg, test_start, xi=xi, blend=blend)
        frames.append(e)
        print(f"    {len(e)} selections", flush=True)
    return pd.concat(frames, ignore_index=True)


def simulate(evals: pd.DataFrame, bet_odds: str = "close", market_blend: float = 1.0,
             edge: float = 0.05, markets: list[str] | None = None,
             min_odds: float = 1.3, max_odds: float = 8.0) -> tuple[pd.DataFrame, dict]:
    """Apply a betting config to the evaluations table. Returns (bets, metrics)."""
    e = evals
    if markets is not None:
        e = e[e["market"].isin(markets)]
    odds = e["odds_open"] if bet_odds == "open" else e["odds_close"]
    fair = e["fair_open"] if bet_odds == "open" else e["fair_close"]

    p_used = market_blend * e["model_p"] + (1 - market_blend) * fair
    ev = p_used * odds - 1.0
    keep = ev.notna() & odds.between(min_odds, max_odds) & (ev > edge)

    b = e[keep].copy()
    b["odds"] = odds[keep]
    b["profit"] = np.where(b["won"], b["odds"] - 1.0, -1.0)
    b["clv"] = b["odds_open"] / b["odds_close"] - 1.0

    if len(b) == 0:
        return b, {"n": 0, "yield": float("nan"), "clv": float("nan"), "beat": float("nan")}
    metrics = {
        "n": len(b),
        "yield": b["profit"].sum() / len(b) * 100,
        "win": b["won"].mean() * 100,
        "clv": b["clv"].mean() * 100,
        "beat": (b["clv"] > 0).mean() * 100,
        "avg_odds": b["odds"].mean(),
    }
    return b, metrics
