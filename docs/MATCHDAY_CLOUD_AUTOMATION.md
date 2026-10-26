# Match-day automation — cloud vs home IP

SofaScore **blocks datacenter IPs**. GitHub-hosted `ubuntu-latest` runners **cannot**
run Playwright against SofaScore, and Cursor Cloud Agents boot in the same class of
environment — so **no true cloud substitute** exists for the live poll without a
**home or self-hosted** execution surface.

What we automate anyway:

| Layer | Runs where | What it does |
|-------|------------|--------------|
| `live_poll.yml` | GitHub cloud | FPL calendar, watchlists, **ICS reminders**, **push nudge** when lineups are due |
| `live_poll_props_selfhosted.yml` | **Self-hosted** runner (home PC) | Full `sofascore_matchday` (goals + props + paper bets) |
| `matchday_laptop.sh` | Your laptop on Wi‑Fi | Same matchday module + optional `git push` |
| `grade_props.yml` / `grade_results.yml` | GitHub cloud | Understat + parquet grading, bankroll settle |
| Web Push | Vercel | New rows **or** “run home poll” nudge |

## Phone / calendar reminders (free)

After each cloud calendar tick, `export_matchday_ics.py` writes
`data/processed/matchday_reminders.ics` with T−90 “start polling” events.

**Subscribe once:**

1. Open the file from the repo on GitHub (raw) or sync locally.
2. Google Calendar → Settings → Import → select the `.ics`, or paste the raw URL if you mirror it.
3. Allow notifications for those events.

This does **not** run the poll — it only reminds you to start
`matchday_laptop.sh` or wake the self-hosted runner.

## Cloud push nudge

`matchday_cloud_nudge.py` runs at the end of `live_poll.yml` when:

- A PL fixture is **15–180 minutes** before kickoff, and
- `live_fixture_health.json` shows **no successful SofaScore poll** yet for that match.

It sends a Web Push (same `NOTIFY_SECRET` as new picks) with the laptop command.
Cooldown: **3 hours** (cached in Actions) to avoid spam.

## Self-hosted runner (best “set and forget”)

Register a runner on a home Mac/PC with labels `self-hosted`, `footymodel-props`.
The workflow `live_poll_props_selfhosted.yml` already mirrors the laptop loop on
`*/20 8-23 * * *` with calendar gating.

## Cursor / other schedulers

- **Cursor Automations** (scheduled agent): useful for docs, grading triage, or
  kicking `workflow_dispatch` — **not** for SofaScore scraping from the cloud VM.
- **Google Calendar MCP**: can create events; use the committed **ICS** instead so
  reminders stay in sync with FPL kickoffs.
- **cron on laptop**: `crontab` calling `matchday_laptop.sh once` during match hours
  is equivalent to the self-hosted runner.

## Pre-flight script

```bash
python scripts/matchday_integration_check.py
python scripts/matchday_schedule.py
```

Run before match day or automatically at the start of `matchday_laptop.sh`.
