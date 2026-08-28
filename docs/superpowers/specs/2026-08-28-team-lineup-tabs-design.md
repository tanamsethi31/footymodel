# Team-wise lineup tabs in Player Props — design

Status: approved

## Purpose

Each match card on the Player Props tab currently lists all 22 confirmed starters
(both teams) in one flat table. Split it into two small tabs — one per team — so a
viewer can look at each side's lineup/props separately instead of scanning a mixed
22-row list.

## Data

No backend or data-layer change. `PropsPick` (`dashboard/lib/data.ts`) already carries
`team` on every row, and `MatchPropsTable`'s `rows` prop already contains every
confirmed starter for both teams in a fixture (`live_player_props.csv` logs one row
per starting player regardless of whether their shots/SOT model matched — see
`footymodel/live/shots_engine.py`'s `player_rows_for_fixture`, which loops over all 11
`startXI` names per side).

## Component change — `dashboard/components/MatchPropsTable.tsx`

Currently: one `useState` (`thresh`) for the 1+/2+/3+ toggle, one flat table over all
`rows`.

Adds: a second `useState` (`activeTeam: 0 | 1`) selecting which of the fixture's two
teams is showing. Team names are derived the same way the match-card header already
does — `[...new Set(rows.map((r) => r.team))]` — reused instead of duplicated.

```tsx
const teams = [...new Set(rows.map((r) => r.team))]; // [home, away] as logged
const [activeTeam, setActiveTeam] = useState(0);
const teamRows = rows.filter((r) => r.team === teams[activeTeam]);
```

The team toggle renders above the existing 1+/2+/3+ toggle, using the **same visual
style** as that toggle (`inline-flex bg-neutral-100 dark:bg-neutral-900 border ...
rounded-lg`, active segment `bg-white dark:bg-neutral-100 text-neutral-900`) — not the
top-level pill-slide/clip-path animation `DashboardTabs` uses. This is a secondary,
nested control and should read as lighter-weight than the primary navigation, per the
existing visual hierarchy (main tabs = animated pill; the 1+/2+/3+ toggle = plain
segmented control). Two visually-loud tab styles nested in one card would compete for
attention.

The threshold toggle (`thresh`/`setThresh`) is unchanged and stays **shared across
both team tabs** — switching from "Crystal Palace" to "Manchester City" keeps whatever
threshold (1+/2+/3+) was selected; there is one threshold state per match card, not
per team.

The table body switches from mapping `rows` to mapping `teamRows`. Table headers
("Player" / "Shots on Target" / "Total Shots") are unchanged — team identity is now
implicit in which tab is active rather than needing a column.

## Layout order (top to bottom, inside each match card)

1. Match header (unchanged: `"{home} v {away}"` + kickoff time)
2. **New**: team toggle (two segments, team names)
3. Threshold toggle (1+/2+/3+) — unchanged, existing `flex justify-end` row
4. Table — now scoped to `teamRows` instead of `rows`

## Edge cases

- Exactly 2 distinct teams per fixture is already guaranteed by how fixtures are
  logged (one row per starter per side) — no need to handle a fixture with a
  different team count.
- `activeTeam` defaults to `0` (first team encountered in the rows array, i.e. the
  home team given how `shots_engine.py` orders its output) — no explicit "home/away"
  ordering logic needed beyond what's already implicit in row order.

## Out of scope

- No change to `PropsPanel.tsx`, `MostProbableStrip.tsx`, or any other tab.
- No change to the underlying data/CSV/Python pipeline.
- No new animation technique — reuses the existing segmented-toggle style verbatim.
