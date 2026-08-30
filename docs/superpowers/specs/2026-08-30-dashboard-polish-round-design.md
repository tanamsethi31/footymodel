# Dashboard Polish Round Design

## Overview

Three independent, small fixes to the footymodel dashboard, bundled as one polish pass before any bigger new-feature work:

1. Upcoming-match lists (Goals O/U, Player Props) aren't sorted by kickoff time, so a match kicking off tomorrow can render above one kicking off in 20 minutes.
2. The Glossary tab's term entries have no visual structure beyond plain text.
3. The Staking tab shows Kelly bankroll simulation numbers with no indication of when they were last generated, even though the underlying script is run manually and irregularly.

None of these touch the model, the live-polling pipeline, or any data the predictions themselves depend on. All three are additive and independently shippable.

## Architecture

No new subsystems. Each item is a small, self-contained change to existing files:

- Item 1 is frontend-only (two `.tsx` files in `dashboard/`).
- Item 2 is frontend-only (one `.tsx` file).
- Item 3 spans one backend script (`scripts/kelly_simulation.py`) and two frontend files (`lib/data.ts`, `StakingPanel.tsx`), connected by one new optional CSV column.

## Components

### 1. Sort-order fix

`dashboard/app/page.tsx`'s `GoalsPanel` and `dashboard/components/PropsPanel.tsx`'s `PropsPanel` both already split their input into `upcoming`/`past` (or `upcomingGroups`/`pastGroups`) by comparing each item's kickoff against `Date.now()`. Neither panel sorts the `upcoming` side, and `getGoalsPicks()`/`getPropsPicks()` in `lib/data.ts` only sort descending (correct for the past side, since `TrackRecordPanel` and the past-disclosure both want most-recently-played-first).

Fix: immediately after computing `upcoming` (or `upcomingGroups`) and `previewFixtures` in each panel, sort ascending by kickoff:

```ts
.sort((a, b) => new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime())
```

- `GoalsPanel`: sort `upcoming` and `previewFixtures`.
- `PropsPanel`: sort `upcomingGroups` (comparing `rows[0].kickoff` on each side) and `previewFixtures`.

`past`/`pastGroups` are untouched — they keep the existing descending order from `lib/data.ts`.

### 2. Glossary blue-accent bars

`dashboard/components/GlossaryPanel.tsx` has 5 sections, each a `<dl>` containing several `<div>` wrappers around a `<dt>`/`<dd>` pair (~16 entries total). Each of those wrapper `<div>`s gets:

```
border-l-2 border-blue-500 dark:border-blue-400 pl-3
```

Section headings (`<h3>` "General concepts", "Track Record terms", etc.) are unchanged — only individual term entries get the accent bar, since the ask was for structure at the point level, not the section level.

### 3. Staking "last updated" stamp

**Backend** (`footymodel/scripts/kelly_simulation.py`): immediately before `result.to_csv(SIM_OUTPUT_PATH, index=False)`, stamp every row with the current time:

```python
result["generated_at"] = pd.Timestamp.now(tz="UTC").isoformat()
```

**Frontend** (`dashboard/lib/data.ts`): `KellySimResult` gets a new field:

```ts
generatedAt: string | null;
```

`getKellySimResults()` parses it the same way every other field is parsed: `generatedAt: r.generated_at ?? null`. A pre-existing CSV generated before this change simply won't have the column, so every row's `generatedAt` will be `null` — handled explicitly, not a crash.

**Frontend** (`dashboard/components/StakingPanel.tsx`): if `results[0].generatedAt` is non-null, append a line to the section's existing subtitle paragraph: `Last run: ${formatKickoff(results[0].generatedAt)}`. `formatKickoff()` (from `lib/format.tsx`) is a generic ISO-string-to-IST formatter despite its kickoff-specific name — reused here for the same reason every other timestamp on the dashboard already goes through it: one consistent IST format everywhere. If `generatedAt` is `null`, the line is omitted entirely (no "unknown" placeholder).

## Data Flow

Item 3 is the only one with a backend-to-frontend flow: `kelly_simulation.py` (run manually) → `data/processed/kelly_simulation.csv` (committed to the repo the same way it already is today, no workflow changes) → `getKellySimResults()` reads it via the existing GitHub Contents API fetch → `StakingPanel` renders it. Items 1 and 2 have no data flow changes; they operate on data already being fetched.

## Error Handling

- Item 1: sorting by `new Date(kickoff).getTime()` can't fail for any kickoff string that already passes today's filtering (`new Date(g.kickoff).getTime() > now`), since that comparison already requires a valid parseable date. No new failure mode.
- Item 3: the only new failure surface is a missing `generated_at` column on old CSVs, handled by `?? null` and the conditional render — never a crash, worst case is just no timestamp line shown.

## Testing

This repo has no frontend test suite (verified: no `.test.`/`.spec.` files under `dashboard/`; all existing automated tests are Python, run via CI). Consistent with that, these changes are verified the same way every other frontend change in this project has been:

- `tsc --noEmit` and `next build` clean.
- Manual check in the dev server: Goals O/U and Player Props show matches in ascending kickoff order; Glossary entries show the blue left-border accent in both light and dark mode; Staking shows (or, pre-deploy with an old CSV, correctly omits) the "Last run" line.
- Item 3's backend half: run `python scripts/kelly_simulation.py` locally and confirm `kelly_simulation.csv` gains a `generated_at` column with a sane UTC timestamp.
