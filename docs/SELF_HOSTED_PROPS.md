# Option A — free live player props (SofaScore + self-hosted)

Training data stays on GitHub Actions (`refresh_training_data.yml`): football-data.co.uk + Understat. **No paid live API.**

Live **player shots/SOT** uses:

| Where | What runs |
|-------|-----------|
| **GitHub `ubuntu-latest`** | `live_poll.yml` — fixture calendar, upcoming list, pre-match watchlists only |
| **Your machine** (self-hosted runner or local cron) | `sofascore_props_engine` — Playwright + confirmed lineups → model probabilities |

SofaScore blocks datacenter IPs (including GitHub-hosted runners). Playwright must run from a normal home/residential network.

## 1. Laptop match-day script (recommended if you only have one machine)

No runner required. On matchdays, on **home Wi‑Fi**:

```bash
./scripts/matchday_laptop.sh show
./scripts/matchday_laptop.sh loop --push
```

`show` prints kickoffs in **Irish time** and when to start polling (~90 minutes before kickoff). `loop` only calls SofaScore when the calendar **gate** says a fixture is in the live window (same logic as GitHub Actions). Use `--push` to commit and push `data/processed/*` so the public dashboard updates.

Keep the laptop **awake** and on Wi‑Fi during that window. A VPS or GitHub cloud runner will not replace this for SofaScore.

## 2. Self-hosted GitHub Actions runner (optional, always-on home PC)

1. On an always-on home PC/Mac: [Add a self-hosted runner](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners) to `tanamsethi31/footymodel`.
2. When configuring labels, include **`footymodel-props`** (matches `live_poll_props_selfhosted.yml`).
3. Ensure the runner machine has Python 3.11 and can `pip install -r requirements.txt` + `playwright install chromium`.
4. Workflow **`Live poll (props — self-hosted)`** runs every 20 minutes in the PL window (same cron as before). It commits `live_player_props.csv`, lineups in `match_detail.jsonl`, and triggers push notifications when `NOTIFY_SECRET` is set on the repo.

Until the runner is online, the cloud calendar job still updates the dashboard preview; props lines simply won’t appear until the self-hosted job succeeds.

## 3. Manual one-shot

```bash
./scripts/poll_props_local.sh
```

Or run `python -m footymodel.live.sofascore_props_engine` directly, then commit/push processed data.

## What you get

- Confirmed starting XI in the dashboard
- Per-player P(shots 1+/2+/3+) and P(SOT 1+/2+)
- **No book odds / EV** in this mode (model-only). Grading vs actual shots still uses post-match WhoScored/FBref (planned).

## What this does *not* use

- API-Football (suspended / paid)
- RapidAPI monthly quota
- Apify pay-per-run
- Anti-bot “bypass” proxies — only a real browser on a non-datacenter IP
