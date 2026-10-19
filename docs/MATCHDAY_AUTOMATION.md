# Match-day automation (how timing works)

Footymodel does **not** schedule one cron job per fixture (GitHub Actions cannot create dynamic crons). Instead it uses the same pattern most small/medium sports-data products use:

1. **Coarse heartbeat** — poll every N minutes during match hours.
2. **Calendar gate** — only run expensive work (Playwright, lineups) when a tracked fixture is inside the **live window** (default: from 24h before kickoff through ~2h after).
3. **Post-match batch** — after Understat publishes rosters, a separate job grades predictions vs actual shots/SOT.

Large companies add **event-driven schedulers** on top of the same idea:

| Pattern | Who uses it | What it does |
|--------|-------------|--------------|
| **Cron + smart gate** | Us, many startups | Cheap ticks; skip when idle (`calendar --gate`). |
| **Per-event schedules** | AWS EventBridge, Google Cloud Scheduler, Temporal | One timer per kickoff (T−90, T−60, T+120). |
| **Queue workers** | FanDuel-scale | Fixture id enqueued at calendar refresh; workers claim jobs. |
| **Streaming** | Live trading | Kafka/PubSub on score/lineup webhooks (paid data). |

We stay on **cron + gate** for cost and simplicity; Irish kickoffs are shown in the app via `Europe/Dublin`.

## What runs automatically in this repo

| Workflow | Where | When (UTC cron) | Purpose |
|----------|--------|-----------------|--------|
| `live_poll.yml` | GitHub cloud | `*/20 8-23 * * *` | Calendar + watchlists (free APIs). |
| `live_poll_props_selfhosted.yml` | **Self-hosted** runner | `*/20 8-23 * * *` | SofaScore lineups → model props (~60–180 min before KO). |
| `grade_props.yml` | GitHub cloud | `08:00`, `23:30` daily | Understat refresh + `backfill_recent_props.py`. |
| `refresh_training_data.yml` | GitHub cloud | daily | Training parquet refresh. |

The **gate** (`python -m footymodel.live.calendar --gate`) sets `should_run=true` only when an unseen fixture is inside `DEFAULT_HOURS_BEHIND` / `DEFAULT_HOURS_AHEAD` (see `footymodel/live/calendar.py`). That is how we align polls with kickoff **without** per-match timers.

## See the next poll windows (Irish time)

```bash
PYTHONPATH=. python scripts/matchday_schedule.py
```

## Local match-day (no self-hosted runner)

```bash
./scripts/poll_props_local.sh   # run ~60–90 minutes before kickoff
```

## Manual grading after a matchweek

```bash
PYTHONPATH=. python -m footymodel.understat --seasons 2026 --leagues E0 --refresh
PYTHONPATH=. python scripts/backfill_recent_props.py -n 10
```
