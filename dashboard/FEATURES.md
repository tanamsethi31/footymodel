# footymodel dashboard — player shots & SOT

Use the **Features** tab on [footymodel.vercel.app](https://footymodel.vercel.app/) for the live checklist (synced with `components/FeaturesPanel.tsx`).

**Repo docs:** [`docs/SHOTS_SOT_OPERATING.md`](../docs/SHOTS_SOT_OPERATING.md),
[`docs/PAPER_PROPS_EXPERIMENT.md`](../docs/PAPER_PROPS_EXPERIMENT.md).

## Live today

- **Product:** Premier League **player shots** (1+/2+/3+) and **SOT** (1+/2+) only
- **Cloud:** fixture calendar + pre-match watchlists (`live_poll.yml`)
- **Home network:** SofaScore Playwright props + **€100 paper bankroll**
  (`matchday_laptop.sh` or `live_poll_props_selfhosted.yml`)
- Confirmed starting XI, per-player probability grids, fixture timeline (Irish time)
- **Track record:** Understat grading + paper bankroll summary when ledger files are committed
- Web Push on new `live_player_props.csv` rows
- Glossary + Features tab

## Partial

- SofaScore **player-prop book odds** (often absent — model-confidence paper stakes used)
- PWA install (manifest without icons)

## Planned

- Prop CLV when closing player lines are captured reliably
- Notification deep links to a fixture card

## Retired

- Goals Over/Under 2.5 live tab and goals Kelly staking tab (research only in repo)
