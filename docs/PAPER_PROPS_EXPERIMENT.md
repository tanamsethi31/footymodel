# €100 paper experiment — props + goals O/U (SofaScore only)

Internal paper trading for **Premier League player shots**, **shots on target**,
and **match Over/Under 2.5** (lineup-aware model). One bankroll, one ledger.
No API-Football, RapidAPI, or Apify on this path.

See also: [`SHOTS_SOT_OPERATING.md`](SHOTS_SOT_OPERATING.md) (match-week playbook).

## Bankroll

- Starting balance: **€100** (`data/processed/paper_props_bankroll.json`)
- Ledger: `data/processed/paper_bankroll_bets.csv` (`bet_kind`: `props` | `goals_ou`)

## When bets are placed

**Player props** — after `sofascore_props_engine` logs a confirmed-lineup fixture:

**Goals O/U** — after `sofascore_engine` logs a row with SofaScore match O/U odds
(same matchday poll, max one 2.5 side per fixture when EV clears the floor).

Props placement rules:

1. **SofaScore odds present** — stake with fractional Kelly (`¼` Kelly, max **2%** of
   current bankroll per bet) on lines with **EV ≥ 2%** (`model_p × odds − 1`).
2. **No player-prop odds** (common on SofaScore) — **model-confidence** stakes:
   flat **1%** of bankroll when `p` clears a line-specific floor (see
   `MIN_P_MODEL_ONLY` in `paper_bankroll.py`).

Goals: ¼ Kelly on the better of over/under when **both** decimal odds exist and
EV ≥ 2%; no model-only goals stakes (odds required).

Caps: at most **12** prop bets, **1** goals bet, and **8%** of bankroll staked
per fixture **combined**.

## Match-day (home Wi‑Fi)

```bash
./scripts/matchday_laptop.sh loop 900 --push
```

This settles any finished bets, polls SofaScore when the calendar gate is open,
places new paper bets, and optionally pushes processed files.

## After matches

`grade_props.yml` grades props from Understat; `grade_results.yml` grades match
totals from `matches.parquet`. Both run `scripts/settle_paper_props.py` to update
the shared bankroll.

```bash
python scripts/paper_props_summary.py
```

## Honest limits

- SofaScore often **does not expose** player shots/SOT odds; most stakes will be
  model-confidence until/unless those markets appear.
- This is forward validation of the shots/SOT models, not a guarantee of profit.
