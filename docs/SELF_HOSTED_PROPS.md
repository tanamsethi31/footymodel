# Option A — free live player props (SofaScore + self-hosted)

Training data stays on GitHub Actions (`refresh_training_data.yml`): football-data.co.uk + Understat. **No paid live API.**

Live **player shots/SOT** uses:

| Where | What runs |
|-------|-----------|
| **GitHub `ubuntu-latest`** | `live_poll.yml` — fixture calendar, upcoming list, pre-match watchlists only |
| **Your machine** (self-hosted runner or local cron) | `sofascore_props_engine` — Playwright + confirmed lineups → model probabilities |

SofaScore blocks datacenter IPs (including GitHub-hosted runners). Playwright must run from a normal home/residential network.

## 1. Self-hosted GitHub Actions runner (recommended)

1. On a always-on home PC/Mac: [Add a self-hosted runner](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners) to `tanamsethi31/footymodel`.
2. When configuring labels, include **`footymodel-props`** (matches `live_poll_props_selfhosted.yml`).
3. Ensure the runner machine has Python 3.11 and can `pip install -r requirements.txt` + `playwright install chromium`.
4. Workflow **`Live poll (props — self-hosted)`** runs every 20 minutes in the PL window (same cron as before). It commits `live_player_props.csv`, lineups in `match_detail.jsonl`, and triggers push notifications when `NOTIFY_SECRET` is set on the repo.

Until the runner is online, the cloud calendar job still updates the dashboard preview; props lines simply won’t appear until the self-hosted job succeeds.

## 2. Local match-day cron (no runner)

From the repo root on your laptop (awake during match windows):

```bash
. .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python -m footymodel.live.sofascore_props_engine
# then commit/push data/processed/* if you want the public dashboard to update
```

Or use `scripts/poll_props_local.sh` (gate + props + optional push instructions).

## What you get

- Confirmed starting XI in the dashboard
- Per-player P(shots 1+/2+/3+) and P(SOT 1+/2+)
- **No book odds / EV** in this mode (model-only). Grading vs actual shots still uses post-match WhoScored/FBref (planned).

## What this does *not* use

- API-Football (suspended / paid)
- RapidAPI monthly quota
- Apify pay-per-run
- Anti-bot “bypass” proxies — only a real browser on a non-datacenter IP
