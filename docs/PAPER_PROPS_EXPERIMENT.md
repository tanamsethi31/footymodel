# €100 paper experiment — player shots & SOT (SofaScore only)

Internal paper trading for **Premier League player shots** and **shots on target**.
No API-Football, RapidAPI, or Apify on this path.

See also: [`SHOTS_SOT_OPERATING.md`](SHOTS_SOT_OPERATING.md) (match-week playbook).

## Bankroll

- Starting balance: **€100** (`data/processed/paper_props_bankroll.json`)
- Ledger: `data/processed/paper_props_bets.csv`

## When bets are placed

After `sofascore_props_engine` logs a confirmed-lineup fixture:

1. **SofaScore odds present** — stake with fractional Kelly (`¼` Kelly, max **2%** of
   current bankroll per bet) on lines with **EV ≥ 2%** (`model_p × odds − 1`).
2. **No player-prop odds** (common on SofaScore) — **model-confidence** stakes:
   flat **1%** of bankroll when `p` clears a line-specific floor (see
   `MIN_P_MODEL_ONLY` in `paper_props_bankroll.py`).

Caps: at most **12** bets and **8%** of bankroll staked per fixture.

## Match-day (home Wi‑Fi)

```bash
./scripts/matchday_laptop.sh loop 900 --push
```

This settles any finished bets, polls SofaScore when the calendar gate is open,
places new paper bets, and optionally pushes processed files.

## After matches

`grade_props.yml` (cloud) grades actual shots/SOT from Understat and runs
`scripts/settle_paper_props.py` to update the bankroll.

```bash
python scripts/paper_props_summary.py
```

## Honest limits

- SofaScore often **does not expose** player shots/SOT odds; most stakes will be
  model-confidence until/unless those markets appear.
- This is forward validation of the shots/SOT models, not a guarantee of profit.
