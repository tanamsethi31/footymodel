# Option A — free live player props (SofaScore + self-hosted)

Training data stays on GitHub Actions (`refresh_training_data.yml`): football-data.co.uk + Understat. **No paid live API.**

Live **player shots/SOT** uses:

| Where | What runs |
|-------|-----------|
| **GitHub `ubuntu-latest`** | `live_poll.yml` — fixture calendar, upcoming list, pre-match watchlists only |
| **Your machine** (self-hosted runner or local cron) | `sofascore_props_engine` — Playwright + confirmed lineups → model probabilities |

SofaScore blocks datacenter IPs (including GitHub-hosted runners). Playwright must run from a normal home/residential network.

## 1. Laptop left at home (plugged in, Wi‑Fi)

No runner required. Leave the machine **at home** on **home Wi‑Fi** (taking it away stops SofaScore polls).

**Before the matchweek**

```bash
cd footymodel   # your clone
git pull origin main
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python3 -m playwright install chromium
PYTHONPATH=. python scripts/matchday_integration_check.py
./scripts/matchday_laptop.sh show
```

**Prevent sleep** (while polling):

- **macOS:** System Settings → Energy → prevent sleep on power adapter; or `sudo pmset -c sleep 0 displaysleep 10`
- **Linux:** disable suspend in power settings, or `systemctl mask sleep.target suspend.target` (distro-dependent)
- **Windows:** Power → “Never” sleep when plugged in

**Run the poll loop** (goals O/U + props + paper bets; only polls when the calendar gate is open):

```bash
cd footymodel && source .venv/bin/activate
./scripts/matchday_laptop.sh loop 900 --push
```

Use **`tmux`** or **`screen`** so the loop survives closing the terminal window. You do **not** need Cursor or a browser open.

For **Sat 31 Oct – Sun 2 Nov 2026**, start the loop around **11:00 Dublin** (first PL kickoff Chelsea v Man Utd 12:30); keep it running through **Sun ~17:00** for Liverpool v Arsenal 16:30.

`--push` commits and pushes `data/processed/*` so [footymodel.vercel.app](https://footymodel.vercel.app/) updates. Optional: set `NOTIFY_SECRET` in the environment if you use Web Push.

**One-shot** (same gate logic, no loop):

```bash
./scripts/matchday_laptop.sh once --push
```

Schedule that with **cron** every 20 minutes on match days if you prefer not to leave a long-running shell (see `docs/MATCHDAY_CLOUD_AUTOMATION.md`).

A VPS or GitHub cloud runner will not replace this for SofaScore.

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
- **€100 internal paper bankroll** (`paper_props_bankroll.json` + `paper_props_bets.csv`) — see
  [`PAPER_PROPS_EXPERIMENT.md`](PAPER_PROPS_EXPERIMENT.md). SofaScore player-prop odds are
  used when present; otherwise model-confidence stakes.

## What this does *not* use

- API-Football (suspended / paid)
- RapidAPI monthly quota
- Apify pay-per-run
- Anti-bot “bypass” proxies — only a real browser on a non-datacenter IP
