# footymodel

A football betting model built on a stats-first hybrid approach. Goal: positive
expected value (ROI) vs. bookmaker closing odds — **not** a high win rate.

See the full plan: `~/.claude/plans/okay-so-i-wanna-snug-sky.md`.

## Core idea

Betting favorites gives a high hit rate and negative returns. We optimize for
**edge vs. the bookmaker's margin-stripped ("fair") probability**. Profit comes
from calibration + value detection + staking discipline, on top of a principled
statistical core (Dixon-Coles / Poisson).

## Layout

```
footymodel/
  config.py    # leagues, seasons, data source URLs, column maps
  data.py      # Phase 1 — download + normalize football-data.co.uk CSVs
data/
  raw/         # downloaded CSVs (gitignored)
  processed/   # normalized tidy table (gitignored)
```

## Setup

```bash
cd ~/footymodel
python3 -m venv .venv
. .venv/bin/activate
pip install pandas numpy scipy matplotlib requests
```

## Phase 1 usage

```bash
. .venv/bin/activate
python -m footymodel.data              # download + normalize default leagues/seasons
python -m footymodel.data --leagues E0 E1 N1 --seasons 2021 2022 2023 2024
```

Output: `data/processed/matches.parquet` — one tidy row per match.

## Betting tool — weekly workflow (Over/Under)

The recommender fits the model on all history and outputs O/U value bets with
fractional-Kelly stakes for upcoming fixtures, logging them for paper-trading.

```bash
. .venv/bin/activate
# Demo on the latest matchday in the dataset (grades vs actual results):
python -m footymodel.recommend --league E1

# Live use next season — supply current fixtures + odds:
#   fixtures.csv columns: home_team,away_team,odds_over25,odds_under25
python -m footymodel.recommend --league E1 --fixtures fixtures.csv
```

Every run appends to `data/processed/paper_trades.csv`. Team names must match
football-data.co.uk spellings (e.g. "Sheffield United", "Nott'm Forest").

> **HONEST STATUS — paper-trade only.** The backtest verdict (`RESULTS.md`) is
> **no edge**: O/U yield ~−7%, Closing Line Value ~−0.2% (negative). The model is
> well-calibrated but cannot beat the market on public data. Track live paper
> results; only consider real money if they turn *positive*, or after adding an
> information edge the market lacks (injuries, lineups, team news).

## Roadmap

- [x] Phase 0 — scaffold
- [x] Phase 1 — data pipeline (`data.py`)
- [x] Phase 2 — Dixon-Coles goals engine (`model.py`)
- [x] Phase 2b — Understat xG integration (`understat.py`)
- [x] Phase 3 — value + backtest harness + CLV (`backtest.py`) → **no edge**
- [x] Phase 4 — O/U market-aware strategy + sweep (`strategy.py`)
- [x] Phase 5 — staking / bankroll (`staking.py`)
- [x] Phase 6 — recommender / paper-trade (`recommend.py`)
