# footymodel dashboard — props-only feature checklist

Use the **Features** tab on [footymodel.vercel.app](https://footymodel.vercel.app/) for the live checklist (same content, kept in sync with `components/FeaturesPanel.tsx`).

## Live today (Option A — free data)

- **Cloud:** fixture calendar + pre-match watchlists (`live_poll.yml`)
- **Self-hosted / home:** SofaScore Playwright props (`live_poll_props_selfhosted.yml` or `scripts/poll_props_local.sh`) — see [docs/SELF_HOSTED_PROPS.md](../docs/SELF_HOSTED_PROPS.md)
- Premier League player shots & SOT predictions (confirmed-lineup window, model-only)
- Today / Upcoming / Past fixture timeline
- Pre-match “players to watch” watchlists
- Confirmed starting XI on logged fixtures
- Per-player probability grids + quick-scan table
- Web Push when new `live_player_props.csv` rows are committed
- Glossary and feature status tab

## Partial

- Book odds & EV on props (when API-Football returns player line markets)
- PWA install (manifest without icons)

## Planned

- Post-match grading vs actual shots/SOT (Track record tab)
- Prop CLV / yield
- Notification deep links to a fixture card

## Retired

- Goals Over/Under 2.5 tab and Kelly staking tab (goals paper-trade)
