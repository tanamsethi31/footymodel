"""Phase C3/C4 — Asian Handicap walk-forward backtest across all 7 leagues.

Two-stage design (mirrors strategy.py): `evaluate_league()` does the expensive
walk-forward (fit per matchday, no lookahead, predict_ah for the actual offered
line), producing one row per fixture with model buckets + all odds variants.
`simulate()` is cheap — applies a betting config (strategy, odds regime, edge/
confidence threshold) to the evaluations and reports yield/CLV/significance.

CLV note: Asian Handicap lines can MOVE between open and close (unlike O/U 2.5
which has a fixed threshold), so opening vs closing odds aren't a clean
same-bet comparison unless the line held. We compute genuine open->close CLV
only on the subset where the line didn't move, and report what fraction of
matches that covers — rather than silently mixing apples and oranges.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from footymodel import config
from footymodel.data import load, PROCESSED_DIR
from footymodel.model import DixonColes, _ah_home_outcome, ah_expected_value
from footymodel.strategy import remove_margin

TEST_START = "2022-07-01"
MIN_TRAIN = 200


def evaluate_league(df: pd.DataFrame, league: str, test_start: str = TEST_START,
                    xi: float = 0.0018, min_train: int = MIN_TRAIN) -> pd.DataFrame:
    league_df = df[df["league"] == league].sort_values("date").reset_index(drop=True)
    test_start = pd.Timestamp(test_start)
    dates = sorted(league_df.loc[league_df["date"] >= test_start, "date"].unique())

    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        train = league_df[league_df["date"] < d]
        if len(train) < min_train:
            continue
        model = DixonColes(xi=xi).fit(train, ref_date=d)

        for r in league_df[league_df["date"] == d].itertuples(index=False):
            if r.home_team not in model.attack or r.away_team not in model.attack:
                continue
            if pd.isna(r.ah_line) or pd.isna(r.ah_odds_h) or pd.isna(r.ah_odds_a):
                continue
            try:
                buckets = model.predict_ah(r.home_team, r.away_team, r.ah_line)
            except KeyError:
                continue

            outcome_h = float(_ah_home_outcome(np.array(r.fthg - r.ftag), r.ah_line))
            fair = remove_margin(np.array([r.ah_odds_h, r.ah_odds_a], dtype=float))

            rows.append({
                "date": d, "league": league, "home": r.home_team, "away": r.away_team,
                "line": r.ah_line, "line_open": r.ah_line_open,
                "line_moved": not np.isclose(r.ah_line, r.ah_line_open, equal_nan=True) if (
                    not pd.isna(r.ah_line_open)) else np.nan,
                "outcome_h": outcome_h,
                "p_home_cover": buckets["p_home_cover"], "p_away_cover": buckets["p_away_cover"],
                "p_push": buckets["p_push"], "fair_p_home": fair[0],
                "odds_h": r.ah_odds_h, "odds_a": r.ah_odds_a,
                "odds_h_max": r.ah_odds_h_max, "odds_a_max": r.ah_odds_a_max,
                "odds_h_open": r.ah_odds_h_open, "odds_a_open": r.ah_odds_a_open,
                "odds_h_maxopen": r.ah_odds_h_maxopen, "odds_a_maxopen": r.ah_odds_a_maxopen,
                **{f"bucket_{k}": v for k, v in buckets.items()},
            })
    return pd.DataFrame(rows)


def build_evaluations(leagues: list[str]) -> pd.DataFrame:
    df = load()
    frames = []
    for lg in leagues:
        print(f"  evaluating {lg} ...", flush=True)
        e = evaluate_league(df, lg)
        print(f"    {len(e)} fixtures", flush=True)
        frames.append(e)
    return pd.concat(frames, ignore_index=True)


def _settle(outcome_h: float, odds_h: float, odds_a: float, side: str) -> float:
    """Realized profit per unit stake for backing `side` ('h' or 'a')."""
    o = outcome_h if side == "h" else -outcome_h
    odds = odds_h if side == "h" else odds_a
    if o > 0:
        return o * (odds - 1.0)
    if o < 0:
        return o * 1.0
    return 0.0


def simulate(evals: pd.DataFrame, strategy: str, odds_regime: str = "avg",
            edge: float = 0.03, min_conf: float = 0.55) -> tuple[pd.DataFrame, dict]:
    """strategy: 'value' (EV>edge) or 'confidence' (bet favoured side if
    p>=min_conf). odds_regime: 'avg' or 'max'."""
    oh_col = "odds_h_max" if odds_regime == "max" else "odds_h"
    oa_col = "odds_a_max" if odds_regime == "max" else "odds_a"
    e = evals.dropna(subset=[oh_col, oa_col]).copy()

    bets = []
    for r in e.itertuples(index=False):
        odds_h, odds_a = getattr(r, oh_col), getattr(r, oa_col)
        buckets = {k[len("bucket_"):]: getattr(r, k) for k in e.columns if k.startswith("bucket_")}
        ev_h, ev_a = ah_expected_value(buckets, odds_h, odds_a)

        if strategy == "value":
            side = None
            if ev_h > edge and ev_h >= ev_a:
                side = "h"
            elif ev_a > edge and ev_a > ev_h:
                side = "a"
        else:  # confidence
            side = "h" if r.p_home_cover >= r.p_away_cover else "a"
            conf = r.p_home_cover if side == "h" else r.p_away_cover
            if conf < min_conf:
                side = None

        if side is None:
            continue
        profit = _settle(r.outcome_h, odds_h, odds_a, side)
        clv = np.nan
        if not r.line_moved and not pd.isna(r.line_moved):
            if odds_regime == "max":
                o_open = r.odds_h_maxopen if side == "h" else r.odds_a_maxopen
            else:
                o_open = r.odds_h_open if side == "h" else r.odds_a_open
            o_close = odds_h if side == "h" else odds_a
            if pd.notna(o_open):
                clv = o_open / o_close - 1.0
        bets.append({"date": r.date, "league": r.league, "side": side,
                    "profit": profit, "odds": odds_h if side == "h" else odds_a,
                    "clv": clv})

    b = pd.DataFrame(bets)
    if b.empty:
        return b, {"n": 0}
    n, profit_sum = len(b), b["profit"].sum()
    se = b["profit"].std() / np.sqrt(n)
    clv_valid = b["clv"].dropna()
    metrics = {
        "n": n, "yield": profit_sum / n * 100,
        "t_stat": (b["profit"].mean() / se) if se > 0 else float("nan"),
        "clv_n": len(clv_valid),
        "clv_mean": clv_valid.mean() * 100 if len(clv_valid) else float("nan"),
        "beat_close": (clv_valid > 0).mean() * 100 if len(clv_valid) else float("nan"),
    }
    return b, metrics


def main():
    leagues = config.DEFAULT_LEAGUES
    eval_path = PROCESSED_DIR / "evals_ah.parquet"
    if eval_path.exists():
        evals = pd.read_parquet(eval_path)
        print(f"Loaded cached AH evaluations: {len(evals)} fixtures")
    else:
        print("Building AH evaluations (walk-forward, per matchday)...")
        evals = build_evaluations(leagues)
        evals.to_parquet(eval_path, index=False)
        print(f"Saved -> {eval_path}")

    line_move_rate = evals["line_moved"].mean() * 100
    print(f"\nLine moved open->close: {line_move_rate:.1f}% of fixtures "
          f"(CLV only computed on the {100-line_move_rate:.1f}% where it held)\n")

    print("=" * 92)
    print(f"{'strategy':>11} {'odds':>5} {'bets':>6} {'yield':>8} {'t-stat':>7} "
          f"{'CLV n':>7} {'CLV%':>7} {'beat%':>6}")
    print("-" * 92)
    all_bets = []
    for strategy in ["confidence", "value"]:
        for regime in ["avg", "max"]:
            bets, m = simulate(evals, strategy=strategy, odds_regime=regime)
            if m["n"] == 0:
                continue
            all_bets.append(bets.assign(strategy=strategy, regime=regime))
            print(f"{strategy:>11} {regime:>5} {m['n']:>6d} {m['yield']:>+7.2f}% "
                  f"{m['t_stat']:>7.2f} {m['clv_n']:>7d} {m['clv_mean']:>+6.2f}% "
                  f"{m['beat_close']:>5.1f}%")
    print("=" * 92)

    print("\nPer-league breakdown (confidence strategy, best-price odds):")
    bets, _ = simulate(evals, strategy="confidence", odds_regime="max")
    for lg, g in bets.groupby("league"):
        y = g["profit"].sum() / len(g) * 100
        se = g["profit"].std() / np.sqrt(len(g))
        t = g["profit"].mean() / se if se > 0 else float("nan")
        print(f"  {lg:4s} n={len(g):5d}  yield={y:+7.2f}%  t={t:+.2f}")


if __name__ == "__main__":
    main()
