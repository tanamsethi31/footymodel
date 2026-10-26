# Operating model — player shots & SOT only

This is the **active product**: Premier League **player shots** (1+/2+/3+) and
**shots on target** (1+/2+), with an internal **€100 paper bankroll**. No real
money, no bookmaker accounts.

Paid live APIs (**API-Football**, **RapidAPI**, **Apify**) are **not used** on
this path — they remain in the repo only as legacy/local fallbacks. Live data is
**SofaScore** (browser/Playwright on a **home IP**).

Historical research on goals O/U, Asian handicap, etc. stays in [`RESULTS.md`](../RESULTS.md);
it is not part of the live dashboard.

## What runs where

| Job | Where | Cost |
|-----|--------|------|
| Fixture calendar + pre-lineup watchlists | GitHub `live_poll.yml` | Free |
| Training parquet refresh | GitHub `refresh_training_data.yml` | Free |
| **Props poll + paper bets** | **Your laptop** or **self-hosted** runner | Free (home Wi‑Fi) |
| Grade actual shots/SOT + settle bankroll | GitHub `grade_props.yml` | Free (Understat) |
| Public dashboard | Vercel | Free |

SofaScore blocks datacenter IPs — GitHub-hosted runners **cannot** replace a
home machine for the props poll.

## Match-week checklist

1. **Before:** `PYTHONPATH=. python scripts/matchday_schedule.py` (Irish kickoffs).
2. **~90 min before first KO until lineups land:** laptop on home Wi‑Fi, awake:
   ```bash
   ./scripts/matchday_laptop.sh loop 900 --push
   ```
3. **After:** grading runs on GitHub twice daily; check:
   ```bash
   python scripts/paper_props_summary.py
   ```

Details: [`MATCHDAY_AUTOMATION.md`](MATCHDAY_AUTOMATION.md), [`SELF_HOSTED_PROPS.md`](SELF_HOSTED_PROPS.md).

## Paper bankroll rules

Full spec: [`PAPER_PROPS_EXPERIMENT.md`](PAPER_PROPS_EXPERIMENT.md).

- State: `data/processed/paper_props_bankroll.json` (starts at **€100**).
- Ledger: `data/processed/paper_props_bets.csv`.
- Stakes: **¼ Kelly** (max 2% of bankroll) when SofaScore player-prop odds exist
  and EV ≥ 2%; otherwise **1%** model-confidence stakes when `p` clears fixed floors.
- Caps: 12 bets / 8% bankroll exposure per fixture.

## Success metrics

- Bankroll curve (ledger + summary script).
- Calibration: shots 1+ / SOT 1+ hit rates on **Track record** (dashboard).
- Share of bets with real SofaScore odds vs model-only pricing.

## Docs index

| Doc | Purpose |
|-----|---------|
| [`PAPER_PROPS_EXPERIMENT.md`](PAPER_PROPS_EXPERIMENT.md) | Staking math + file paths |
| [`SELF_HOSTED_PROPS.md`](SELF_HOSTED_PROPS.md) | Runner vs laptop setup |
| [`MATCHDAY_AUTOMATION.md`](MATCHDAY_AUTOMATION.md) | Cron + calendar gate |
| [`README.md`](../README.md) | Repo overview |
