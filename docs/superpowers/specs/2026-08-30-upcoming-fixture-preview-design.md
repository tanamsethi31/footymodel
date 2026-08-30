# Upcoming Fixture Preview — Design

## Goal

The Goals O/U and Player Props tabs currently show nothing for a fixture until its lineup is confirmed and a real prediction is logged — so between matchdays (or whenever no fixture currently has a confirmed lineup), both tabs go completely blank aside from the past-predictions disclosure. This adds a preview of the next Premier League fixtures — team names and kickoff time, with a plain "analysis pending" line in place of numbers that don't exist yet — so there's always visibility into what's coming up next, even before any real analysis has happened.

## Background

API-Football's free tier restricts date-based fixture queries to a rolling 3-day window (confirmed directly: querying today+2 days succeeds, today+3 fails with "Free plans do not have access to this date"). The `next=N` fixtures parameter is blocked entirely on the free tier regardless of season. So "next fixtures" here means "whatever falls within the accessible 3-day window," not a guaranteed complete round — in practice this usually covers all or most of the next matchday, since Premier League rounds cluster over a weekend.

`run_all.py`'s `run_once()` already fetches E0 fixtures for today+tomorrow (`all_fixtures`, feeding both the goals and player-props engines); this design extends that same fetch to include the day after, and writes every E0 fixture found — regardless of whether its lineup is confirmed yet — to a new file.

## Backend: `upcoming_fixtures.json`

`data/processed/upcoming_fixtures.json`, a plain JSON array, fully rewritten each poll (not appended-to, since it's meant to reflect "what's coming up right now," not an accumulating history):

```json
[
  {"fixture_id": 123, "home": "Chelsea", "away": "Brighton", "kickoff": "2026-08-30T13:00:00+00:00"}
]
```

In `run_all.py`'s `run_once()`, the date-range fetch loop (currently `{today, tomorrow}`) extends to `{today, tomorrow, day-after}`. A new pure function, `build_upcoming_list(all_fixtures, api_id_to_div)`, filters `all_fixtures` down to fixtures whose league is in `api_id_to_div` (currently just E0) and shapes each into the `{fixture_id, home, away, kickoff}` dict above — this is the one piece of genuinely testable logic here, so it's extracted rather than inlined, matching how `match_detail.py`'s functions are structured. The resulting list is written to `upcoming_fixtures.json` after the existing goal/prop row writes, in its own try/except (a write failure here must never affect the real prediction rows, same principle as `match_detail.py`).

No fixture-status filtering happens here — the file lists every near-term E0 fixture whether or not it already has a confirmed-lineup prediction. That filtering is the frontend's job (see below), since it already needs to look up each fixture's real prediction anyway.

`.gitignore` needs `!data/processed/upcoming_fixtures.json` and `live_poll.yml`'s commit step needs the file added to its `git add` list — both required from the start (a prior feature this session shipped without either and it silently never reached production until caught in review).

## Frontend

**Data layer** (`dashboard/lib/data.ts`): a new type,

```typescript
export type UpcomingFixture = {
  fixtureId: string;
  home: string;
  away: string;
  kickoff: string;
};
```

and `getUpcomingFixtures(): Promise<UpcomingFixture[]>`, fetching `upcoming_fixtures.json` via the GitHub Contents API (same auth/404-means-empty pattern as `fetchCsv`/`fetchJsonl`), parsed as a single JSON array rather than line-by-line.

**Component** (`dashboard/components/PreviewMatchCard.tsx`, new): deliberately not a variant of `MatchCard` — it has no interactivity at all, no click, no chevron, no expand state. Just the team names, kickoff time (via the same `formatKickoff()`), and one muted line: *"Analysis available once lineups are confirmed (~20-40min pre-kickoff)."* Same card shell (rounded border, padding) as `MatchCard` so it visually reads as part of the same list, while being clearly inert — no hover-lift, no cursor-pointer.

**Wiring**: both `GoalsPanel` (in `page.tsx`) and `PropsPanel.tsx` compute their own preview list — `upcomingFixtures` filtered to drop any `fixtureId` already present in real data (`goals` for Goals O/U, `propsByFixture`'s keys for Player Props) — and render the remainder as `PreviewMatchCard`s. Ordering: real upcoming predictions, then preview cards, then the collapsed past-predictions `PastDisclosure`, matching the site's existing "most-actionable-first" ordering. `Home()` fetches `getUpcomingFixtures()` alongside everything else and passes it to both panels.

A fixture whose lineup gets confirmed mid-window (a real prediction lands for it) simply disappears from the preview list and appears in the real-predictions section instead on the next data refresh — this falls out of the filtering logic automatically, no special-casing needed.

## Error handling

- Missing `upcoming_fixtures.json` (e.g. before the first post-deploy poll runs): same "404 → empty array" handling already used everywhere else — no preview cards render, nothing breaks.
- The day-after-tomorrow fetch failing doesn't block existing goals/props processing — each date's fetch already has its own try/except; a failed fetch for one date just means a shorter preview list that poll.
- Writing `upcoming_fixtures.json` failing doesn't affect the real prediction rows — isolated in its own try/except after they're already written.

## Testing

- A data-free Python unit test for `build_upcoming_list()` (matching `scripts/match_detail_test.py`'s style), covering: fixtures in tracked leagues are included and shaped correctly, fixtures in untracked leagues are excluded, an empty input returns an empty list. Wired into CI.
- No new dashboard test — verified the same way as every other frontend change (`tsc --noEmit`, `next build`, browser check).

## Out of scope

- Guaranteeing the complete next round regardless of how far out it is (would need a different, non-free-tier data source).
- Showing preview cards for any league besides Premier League (E0) — matches the live engines' existing scope.
- Any interactivity on preview cards (no expand, no click) — there's nothing to expand into yet.
