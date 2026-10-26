# Operating model — SofaScore paper trading (props + goals O/U)

**Active product:** Premier League **player shots** (1+/2+/3+) and **shots on
target** (1+/2+), plus lineup-aware **Over/Under 2.5 goals**, on one internal
**€100 paper bankroll**. No real money, no bookmaker accounts.

Paid live APIs (**API-Football**, **RapidAPI**, **Apify**) are **not used** on
this path — they remain in the repo only as legacy/local fallbacks. Live data is
**SofaScore** (browser/Playwright on a **home IP**).

Closing-line goals backtests in [`RESULTS.md`](../RESULTS.md) showed **no edge**;
the live hypothesis is the **confirmed-lineup window** (same as props). Treat
goals O/U paper bets as forward validation, not a profit guarantee.

## What runs where

| Job | Where | Cost |
|-----|--------|------|
| Fixture calendar + pre-lineup watchlists | GitHub `live_poll.yml` | Free |
| Training parquet refresh | GitHub `refresh_training_data.yml` | Free |
| **Matchday poll** (goals O/U + props + paper bets) | **Your laptop** or **self-hosted** runner | Free (home Wi‑Fi) |
| Grade props + settle bankroll | GitHub `grade_props.yml` | Free (Understat) |
| Grade match totals + settle goals bets | GitHub `grade_results.yml` | Free (`matches.parquet`) |
| Public dashboard | Vercel | Free |

SofaScore blocks datacenter IPs — GitHub-hosted runners **cannot** replace a
home machine for the matchday poll.

## Match-week checklist

1. **Before:** `PYTHONPATH=. python scripts/matchday_schedule.py` (Irish kickoffs).
2. **~90 min before first KO until lineups land:** laptop on home Wi‑Fi, awake:
   ```bash
   ./scripts/matchday_laptop.sh loop 900 --push
   ```
   One Playwright session runs **goals** then **player props** (`sofascore_matchday`).
3. **After:** grading runs on GitHub; check:
   ```bash
   python scripts/paper_props_summary.py
   ```

Details: [`MATCHDAY_AUTOMATION.md`](MATCHDAY_AUTOMATION.md), [`MATCHDAY_CLOUD_AUTOMATION.md`](MATCHDAY_CLOUD_AUTOMATION.md), [`SELF_HOSTED_PROPS.md`](SELF_HOSTED_PROPS.md).

**Automation:** cloud job refreshes `matchday_reminders.ics` and can Web Push when a
home poll is due; run `python scripts/matchday_integration_check.py` before match day.

## Paper bankroll rules

Full spec: [`PAPER_PROPS_EXPERIMENT.md`](PAPER_PROPS_EXPERIMENT.md). Plan: [`GOALS_OU_PAPER_PLAN.md`](GOALS_OU_PAPER_PLAN.md).

- State: `data/processed/paper_props_bankroll.json` (starts at **€100**).
- Ledger: `data/processed/paper_bankroll_bets.csv` (legacy `paper_props_bets.csv` still read).
- **Props:** ¼ Kelly (max 2% of bankroll) when SofaScore player-prop odds exist and EV ≥ 2%; otherwise 1% model-confidence floors.
- **Goals O/U 2.5:** at most **one** side per fixture when both SofaScore match O/U odds exist and best-side EV ≥ 2%; ¼ Kelly, max 2%.
- Caps: **12** prop bets per fixture, **1** goals bet per fixture, **8%** total stake exposure per fixture **across props + goals**.

## Success metrics

- Bankroll curve (ledger + summary script).
- Props calibration on **Track record** (shots 1+ / SOT 1+ vs Understat).
- Goals O/U hit rate vs model on finished fixtures (`live_recommendations.csv` + graded results).
- Share of bets with real SofaScore odds vs model-only pricing (props).

## Docs index

| Doc | Purpose |
|-----|---------|
| [`PAPER_PROPS_EXPERIMENT.md`](PAPER_PROPS_EXPERIMENT.md) | Staking math + file paths |
| [`GOALS_OU_PAPER_PLAN.md`](GOALS_OU_PAPER_PLAN.md) | Goals re-enable checklist |
| [`SELF_HOSTED_PROPS.md`](SELF_HOSTED_PROPS.md) | Runner vs laptop setup |
| [`MATCHDAY_AUTOMATION.md`](MATCHDAY_AUTOMATION.md) | Cron + calendar gate |
| [`README.md`](../README.md) | Repo overview |
