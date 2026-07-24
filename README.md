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

## Roadmap

- [x] Phase 0 — scaffold
- [ ] Phase 1 — data pipeline
- [ ] Phase 2 — Dixon-Coles goals engine (xG-adjusted)
- [ ] Phase 3 — value + backtest harness (the go/no-go gate)
- [ ] Phase 4 — optional ML layer
- [ ] Phase 5 — staking / bankroll rules
- [ ] Phase 6 — deployment (paper-trade first)
