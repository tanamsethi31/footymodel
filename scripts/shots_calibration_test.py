"""Calibration check for the player-shots probability model. No odds/edge to
test (none exist for this market) - the only question is: when we say 60%,
does it happen ~60% of the time?

Two-stage: `evaluate()` does the expensive walk-forward once, caching each
player-match's fitted RATE (not yet converted to a probability). `simulate()`
applies prob_over() with any dispersion value cheaply on the cached rates, so
sweeping Poisson vs Negative-Binomial dispersion doesn't require re-fitting.

ponytail: MINUTES_ASSUMED=85 is the measured league-wide average minutes for a
starter (flat 90 measurably broke calibration - checked). Per-player expected
minutes would be more precise; upgrade path if a specific player's calibration
looks off (e.g. a known rotation risk).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from footymodel.backtest import calibration_table
from footymodel.players import LineupModel, load_players, prob_over

LEAGUES = sys.argv[1].split(",") if len(sys.argv) > 1 else ["E0", "SP1", "D1", "I1", "F1"]
LINES = [0.5, 1.5, 2.5]
TEST_START = "2022-07-01"
MIN_TRAIN_ROWS = 5000
MINUTES_ASSUMED = 85  # see ponytail note above
CACHE = Path(__file__).resolve().parent.parent / "data" / "processed" / "shots_eval_cache.parquet"


def evaluate(players: pd.DataFrame, leagues: list[str]) -> pd.DataFrame:
    rows = []
    for league in leagues:
        lp = players[players["league"] == league]
        meta = lp.groupby("match_id").agg(date=("date", "first"),
                                          home_us=("home_us", "first"),
                                          away_us=("away_us", "first")).reset_index()
        dates = sorted(meta.loc[meta.date >= pd.Timestamp(TEST_START), "date"].unique())
        for d in dates:
            d = pd.Timestamp(d)
            if len(lp[lp["date"] < d]) < MIN_TRAIN_ROWS:
                continue
            model = LineupModel.fit(players, league, d)
            day = lp[(lp["date"] == d) & lp["started"]]
            for m in meta[meta.date == d].itertuples(index=False):
                for r in day[day["match_id"] == m.match_id].itertuples(index=False):
                    opponent = m.away_us if r.side == "h" else m.home_us
                    rate = model.shots_ratings.get(r.player_id, model.shots_fallback)
                    rate *= model.opp_shots_fac.get(opponent, 1.0)
                    rows.append({"league": league, "rate": rate, "shots": r.shots})
    return pd.DataFrame(rows)


def simulate(evals: pd.DataFrame, dispersion: float | None = None) -> None:
    from scipy.stats import nbinom, poisson
    lam = evals["rate"].values * MINUTES_ASSUMED / 90.0
    for line in LINES:
        if dispersion is None:
            p = 1.0 - poisson.cdf(np.floor(line), lam)
        else:
            n, prm = dispersion, dispersion / (dispersion + lam)
            p = 1.0 - nbinom.cdf(np.floor(line), n, prm)
        won = (evals["shots"] > line).values
        brier = np.mean((p - won) ** 2)
        tag = "Poisson" if dispersion is None else f"NB(disp={dispersion})"
        print(f"=== line {line} [{tag}] — n={len(p)} — Brier {brier:.4f} ===")
        print(calibration_table(pd.DataFrame({"p": p, "won": won}))
              .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
        print()


if __name__ == "__main__":
    if CACHE.exists():
        evals = pd.read_parquet(CACHE)
        print(f"Loaded cached evaluations: {len(evals)} rows")
    else:
        print("Evaluating (walk-forward, per matchday)...")
        evals = evaluate(load_players(), LEAGUES)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        evals.to_parquet(CACHE, index=False)
        print(f"Saved -> {CACHE}")

    dispersion = float(sys.argv[2]) if len(sys.argv) > 2 else None
    simulate(evals, dispersion)
