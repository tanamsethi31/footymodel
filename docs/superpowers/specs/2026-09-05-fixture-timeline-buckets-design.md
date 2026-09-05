# Fixture timeline buckets — Design

## Goal

Matches should flow through three dashboard stages by kickoff time:

1. **Preview** — next 5 scheduled fixtures on future matchdays (not today). Placeholder cards until lineups are confirmed (~20–40 min pre-kickoff).
2. **Today** — every fixture kicking off today (UTC). Full goals/props analysis when logged; preview card until then.
3. **Past predictions** — every fixture whose kickoff has passed, in kickoff order (oldest → newest), with full expandable analysis (XI, shots/SOT 1+/2+/3+).

## Rules

| Bucket | Kickoff condition | Limit |
|--------|-------------------|-------|
| Past | `kickoff <= now` | all logged matches |
| Today | `kickoff > now` and calendar date is today (UTC) | all |
| Preview | `kickoff > now` and calendar date after today (UTC) | 5 |

A fixture moves **Preview → Today** at UTC midnight on matchday, then **Today → Past** at kickoff.

## Frontend

- New `dashboard/lib/fixtureTimeline.ts` — pure bucketing + `findLoggedFixture()` keyed by fixture id or `home|away|date`.
- `GoalsPanel` and `PropsPanel` render three sections with shared ordering.
- Past disclosure keeps collapse UX but lists **all** past rows sorted ascending by kickoff.

## Out of scope

- Changing live-engine poll windows or backfilling unlogged past fixtures.
- Timezone per-user (UTC only, same as stored kickoffs).
