# Upcoming Fixture Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Goals O/U and Player Props tabs show a preview of upcoming Premier League fixtures (team names, kickoff) with a plain "analysis pending" line, instead of showing nothing until a lineup is confirmed.

**Architecture:** `run_all.py`'s existing fixture fetch (today+tomorrow, feeding both live engines) extends to a 3rd day and writes every tracked-league fixture found — regardless of confirmed-lineup status — to a new `data/processed/upcoming_fixtures.json`. The dashboard fetches this the same way it fetches everything else (GitHub Contents API), and each tab computes its own preview list by excluding fixtures it already has a real prediction for.

**Tech Stack:** Python (pandas, existing `footymodel.live` package), Next.js App Router / TypeScript / Tailwind (existing `dashboard/` app).

**Spec:** `docs/superpowers/specs/2026-08-30-upcoming-fixture-preview-design.md`

---

### Task 1: `build_upcoming_list()` + wire into `run_all.py`

**Files:**
- Modify: `footymodel/live/run_all.py`
- Create: `scripts/run_all_upcoming_test.py`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the failing test**

```python
# scripts/run_all_upcoming_test.py
"""Unit-check for run_all.py's build_upcoming_list() - shapes API-Football
fixture dicts into the small preview record the dashboard shows for matches
that don't have a confirmed-lineup prediction yet (fixture_id, home, away,
kickoff only - no lineup/odds/model data, since none of that exists yet for
these fixtures). Doesn't check confirmation status itself - the dashboard
does that by cross-referencing fixture_id against what it already has.
Pure/data-free - safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.run_all import build_upcoming_list

api_id_to_div = {39: "E0"}

fixtures = [
    {
        "fixture": {"id": 111, "date": "2026-08-30T13:00:00+00:00"},
        "league": {"id": 39},
        "teams": {"home": {"name": "Chelsea"}, "away": {"name": "Brighton"}},
    },
    {
        "fixture": {"id": 222, "date": "2026-08-30T15:00:00+00:00"},
        "league": {"id": 140},  # La Liga - not a tracked league
        "teams": {"home": {"name": "Barcelona"}, "away": {"name": "Real Madrid"}},
    },
]

result = build_upcoming_list(fixtures, api_id_to_div)
assert result == [
    {"fixture_id": 111, "home": "Chelsea", "away": "Brighton",
     "kickoff": "2026-08-30T13:00:00+00:00"},
], result
assert len(result) == 1, "the untracked-league fixture must be excluded entirely"

assert build_upcoming_list([], api_id_to_div) == []

print("run_all_upcoming_test: OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/run_all_upcoming_test.py`
Expected: `ImportError: cannot import name 'build_upcoming_list' from 'footymodel.live.run_all'`

- [ ] **Step 3: Add `build_upcoming_list()` and `UPCOMING_LOG` to `run_all.py`**

Add `import json` to the top of the import block (after `from __future__ import annotations`, before `import pandas as pd`):

```python
from __future__ import annotations

import json

import pandas as pd
```

Add, after the module docstring's imports (right after `from .shots_engine import PROPS_LOG, PropsWatcher`):

```python
UPCOMING_LOG = PROCESSED_DIR / "upcoming_fixtures.json"


def build_upcoming_list(all_fixtures: list[dict], api_id_to_div: dict[int, str]) -> list[dict]:
    """Shape every fixture in a tracked league into the small preview record
    the dashboard shows for matches without a confirmed-lineup prediction
    yet. Doesn't check confirmation status - the dashboard does that itself
    by cross-referencing fixture_id against what it already has."""
    upcoming = []
    for fx in all_fixtures:
        if api_id_to_div.get(fx["league"]["id"]) is None:
            continue
        upcoming.append({
            "fixture_id": fx["fixture"]["id"],
            "home": fx["teams"]["home"]["name"],
            "away": fx["teams"]["away"]["name"],
            "kickoff": fx["fixture"]["date"],
        })
    return upcoming
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/run_all_upcoming_test.py`
Expected: `run_all_upcoming_test: OK`

- [ ] **Step 5: Extend the date-range fetch to 3 days and write `upcoming_fixtures.json`**

In `run_once()`, change:

```python
    all_fixtures = []
    for date_str in {now.strftime("%Y-%m-%d"), (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d")}:
        try:
            all_fixtures.extend(client.fixtures_by_date(date_str))
        except ApiFootballError as e:
            print(f"! fixtures fetch failed for {date_str}: {e}")
```

to:

```python
    all_fixtures = []
    for date_str in {now.strftime("%Y-%m-%d"),
                     (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                     (now + pd.Timedelta(days=2)).strftime("%Y-%m-%d")}:
        try:
            all_fixtures.extend(client.fixtures_by_date(date_str))
        except ApiFootballError as e:
            print(f"! fixtures fetch failed for {date_str}: {e}")

    try:
        upcoming = build_upcoming_list(all_fixtures, api_id_to_div)
        UPCOMING_LOG.parent.mkdir(parents=True, exist_ok=True)
        UPCOMING_LOG.write_text(json.dumps(upcoming))
    except Exception as e:
        print(f"  ! failed to write upcoming_fixtures.json (predictions themselves unaffected): {e}")
```

(This is a 3rd day added to the existing 2-day fetch - API-Football's free tier allows querying up to 2 days ahead of today, confirmed directly. The write happens right after the fetch, before the confirmed-lineup processing loop, since it only needs `all_fixtures`/`api_id_to_div` - already computed above this point - and must never be skipped or corrupted by anything that happens later in the function.)

- [ ] **Step 6: Verify with the existing dry-run script**

Run: `python scripts/run_all_dryrun.py`
Expected: `ALL CHECKS PASSED — shared fetch confirmed, no duplicate API-Football calls.` (this script mocks the API client; confirm by eye that no traceback appears - `UPCOMING_LOG`'s override is added in Task 2, so this run will write to the REAL tracked `data/processed/upcoming_fixtures.json` for now - check `git status` shows it changed, and revert it with `git checkout -- data/processed/upcoming_fixtures.json` if so, since Task 2 fixes this properly)

- [ ] **Step 7: Wire into CI**

In `.github/workflows/ci.yml`, add this step after the existing "Player-roster incremental merge logic" step:

```yaml
      - name: Upcoming-fixture preview list building (pure, data-free)
        run: python scripts/run_all_upcoming_test.py
```

- [ ] **Step 8: Commit**

```bash
git add footymodel/live/run_all.py scripts/run_all_upcoming_test.py .github/workflows/ci.yml
git commit -m "feat: add upcoming_fixtures.json preview list to run_all.py"
```

---

### Task 2: Production data-path fixes (gitignore, cron commit list, dry-run isolation)

**Files:**
- Modify: `.gitignore`
- Modify: `.github/workflows/live_poll.yml`
- Modify: `scripts/run_all_dryrun.py`

Three earlier features this session each needed this same category of fix after shipping without it (a file gets written locally but never reaches the repo, or a dry-run test pollutes the real tracked file) - doing all three up front here instead.

- [ ] **Step 1: Add the gitignore negation**

In `.gitignore`, add `!data/processed/upcoming_fixtures.json` to the "Tracked exceptions" block, alongside the other negations (e.g. right after `!data/processed/match_detail.jsonl`):

```
!data/processed/match_detail.jsonl
!data/processed/upcoming_fixtures.json
```

- [ ] **Step 2: Verify the negation works**

Run: `mkdir -p data/processed && echo '[]' > data/processed/upcoming_fixtures.json && git add data/processed/upcoming_fixtures.json && git status --short data/processed/upcoming_fixtures.json`
Expected: `A  data/processed/upcoming_fixtures.json` (staged successfully, not rejected as ignored)

Then unstage it (it's just a verification artifact, not real data yet): `git reset data/processed/upcoming_fixtures.json && rm data/processed/upcoming_fixtures.json`

- [ ] **Step 3: Add the file to the cron's commit list**

In `.github/workflows/live_poll.yml`, the file list in the "Commit + push any new recommendations/state" step currently reads:

```yaml
          for f in data/processed/live_seen_fixtures.json \
                   data/processed/live_recommendations.csv \
                   data/processed/live_player_props.csv \
                   data/processed/match_detail.jsonl \
                   data/processed/sofascore_seen_fixtures.json \
                   data/processed/rapidapi_seen_fixtures.json \
                   data/processed/rapidapi_budget.json \
                   data/processed/rapidapi_fixtures_cache.json; do
```

Add `data/processed/upcoming_fixtures.json` to it:

```yaml
          for f in data/processed/live_seen_fixtures.json \
                   data/processed/live_recommendations.csv \
                   data/processed/live_player_props.csv \
                   data/processed/match_detail.jsonl \
                   data/processed/upcoming_fixtures.json \
                   data/processed/sofascore_seen_fixtures.json \
                   data/processed/rapidapi_seen_fixtures.json \
                   data/processed/rapidapi_budget.json \
                   data/processed/rapidapi_fixtures_cache.json; do
```

- [ ] **Step 4: Isolate the dry-run script from the real tracked file**

In `scripts/run_all_dryrun.py`, the existing overrides read:

```python
engine.SEEN_FIXTURES_FILE = tmp / "seen.json"
engine.LIVE_LOG = tmp / "goals.csv"
run_all.LIVE_LOG = engine.LIVE_LOG
shots_engine.PROPS_LOG = tmp / "props.csv"
run_all.PROPS_LOG = shots_engine.PROPS_LOG
match_detail.MATCH_DETAIL_LOG = tmp / "match_detail.jsonl"
```

Add one more line:

```python
engine.SEEN_FIXTURES_FILE = tmp / "seen.json"
engine.LIVE_LOG = tmp / "goals.csv"
run_all.LIVE_LOG = engine.LIVE_LOG
shots_engine.PROPS_LOG = tmp / "props.csv"
run_all.PROPS_LOG = shots_engine.PROPS_LOG
match_detail.MATCH_DETAIL_LOG = tmp / "match_detail.jsonl"
run_all.UPCOMING_LOG = tmp / "upcoming_fixtures.json"
```

(`UPCOMING_LOG` is defined directly in `run_all.py`, unlike `LIVE_LOG`/`PROPS_LOG` which are imported from `engine.py`/`shots_engine.py` - so only this one override is needed, no `engine.UPCOMING_LOG` counterpart exists.)

- [ ] **Step 5: Verify**

Run: `python scripts/run_all_dryrun.py`
Expected: `ALL CHECKS PASSED — shared fetch confirmed, no duplicate API-Football calls.`

Run: `git status --short data/processed/upcoming_fixtures.json`
Expected: no output (the dry run no longer touches the real tracked file)

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/live_poll.yml'))"`
Expected: no output (YAML still valid)

- [ ] **Step 6: Commit**

```bash
git add .gitignore .github/workflows/live_poll.yml scripts/run_all_dryrun.py
git commit -m "fix: gitignore/cron-commit-list/dry-run isolation for upcoming_fixtures.json"
```

---

### Task 3: Frontend data layer

**Files:**
- Modify: `dashboard/lib/data.ts`

- [ ] **Step 1: Add the `UpcomingFixture` type**

Add near the other type definitions (after the `MatchDetail` type, before `GradedResult`):

```typescript
export type UpcomingFixture = {
  fixtureId: string;
  home: string;
  away: string;
  kickoff: string;
};
```

- [ ] **Step 2: Add a plain-JSON fetch helper**

Add right after the existing `fetchJsonl()` function:

```typescript
async function fetchJson(name: string): Promise<unknown[]> {
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw new Error("GITHUB_TOKEN not set");
  const res = await fetch(
    `https://api.github.com/repos/${REPO}/contents/${DATA_PATH}/${name}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github.raw+json",
      },
      next: { revalidate: 60 },
    }
  );
  if (res.status === 404) return []; // file doesn't exist yet
  if (!res.ok) throw new Error(`Failed to fetch ${name}: ${res.status} ${await res.text()}`);
  const text = await res.text();
  return JSON.parse(text);
}
```

- [ ] **Step 3: Add `getUpcomingFixtures()`**

Add after `getMatchDetails()`:

```typescript
export async function getUpcomingFixtures(): Promise<UpcomingFixture[]> {
  const rows = (await fetchJson("upcoming_fixtures.json")) as Record<string, unknown>[];
  return rows
    .map((r) => ({
      fixtureId: String(r.fixture_id),
      home: String(r.home),
      away: String(r.away),
      kickoff: String(r.kickoff),
    }))
    .filter((f) => f.fixtureId && f.home && f.away);
}
```

- [ ] **Step 4: Verify**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no output

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/data.ts
git commit -m "feat: fetch upcoming_fixtures.json in the dashboard data layer"
```

---

### Task 4: `PreviewMatchCard` component

**Files:**
- Create: `dashboard/components/PreviewMatchCard.tsx`

- [ ] **Step 1: Write the component**

```tsx
// dashboard/components/PreviewMatchCard.tsx
import type { UpcomingFixture } from "@/lib/data";
import { formatKickoff } from "@/lib/format";

export default function PreviewMatchCard({
  fixture,
  index,
}: {
  fixture: UpcomingFixture;
  index: number;
}) {
  return (
    <div
      className="animate-stagger-in rounded-xl border border-neutral-200 dark:border-neutral-800 p-4"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className="font-medium">
          {fixture.home} v {fixture.away}
        </span>
        <span className="text-xs text-neutral-500">{formatKickoff(fixture.kickoff)}</span>
      </div>
      <p className="mt-3 text-xs text-neutral-400">
        Analysis available once lineups are confirmed (~20-40min pre-kickoff).
      </p>
    </div>
  );
}
```

No `"use client"` directive - this component has no interactivity (no `useState`, no event handlers beyond none), so it renders fine as a plain Server Component, unlike `MatchCard` which needs client-side state for its expand/collapse.

- [ ] **Step 2: Verify**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/PreviewMatchCard.tsx
git commit -m "feat: add PreviewMatchCard component"
```

---

### Task 5: Wire preview fixtures into both tabs

**Files:**
- Modify: `dashboard/app/page.tsx`
- Modify: `dashboard/components/PropsPanel.tsx`

- [ ] **Step 1: Update imports in `page.tsx`**

Change:

```typescript
import {
  getGoalsPicks,
  getPropsPicks,
  getGradedResults,
  getMostProbablePicks,
  getKellySimResults,
  getMatchDetails,
  type GoalsPick,
  type GradedResult,
  type MatchDetail,
} from "@/lib/data";
```

to:

```typescript
import {
  getGoalsPicks,
  getPropsPicks,
  getGradedResults,
  getMostProbablePicks,
  getKellySimResults,
  getMatchDetails,
  getUpcomingFixtures,
  type GoalsPick,
  type GradedResult,
  type MatchDetail,
  type UpcomingFixture,
} from "@/lib/data";
```

Add, after the `MatchCard` import:

```typescript
import PreviewMatchCard from "@/components/PreviewMatchCard";
```

- [ ] **Step 2: Update `GoalsPanel` to include preview fixtures**

Replace the whole `GoalsPanel` function with:

```tsx
function GoalsPanel({
  goals,
  matchDetails,
  upcomingFixtures,
}: {
  goals: GoalsPick[];
  matchDetails: Record<string, MatchDetail>;
  upcomingFixtures: UpcomingFixture[];
}) {
  // A match that's already kicked off isn't a live pick anymore - it moves
  // into the collapsed "past predictions" disclosure below instead of
  // cluttering the upcoming list (still checkable, just out of the way).
  const now = Date.now();
  const upcoming = goals.filter((g) => new Date(g.kickoff).getTime() > now);
  const past = goals.filter((g) => new Date(g.kickoff).getTime() <= now);
  // Any upcoming fixture that doesn't have a real prediction yet shows as a
  // preview card instead - once its lineup is confirmed it'll show up in
  // `goals` above and drop out of this list automatically.
  const predictedFixtureIds = new Set(goals.map((g) => g.fixtureId));
  const previewFixtures = upcomingFixtures.filter(
    (f) => !predictedFixtureIds.has(f.fixtureId)
  );
  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Goals: Over/Under 2.5</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Confirmed-lineup model, pooled t=3.04 backtested (individually
        significant on the Premier League alone, t=2.23).
      </p>
      {upcoming.length === 0 && previewFixtures.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No upcoming predictions right now. Check back once a fixture&apos;s
          lineup is confirmed pre-kickoff.
        </p>
      ) : (
        <div className="space-y-3">
          {upcoming.map((g, i) => (
            <MatchCard
              key={g.fixtureId}
              match={g}
              detail={matchDetails[g.fixtureId] ?? null}
              index={i}
            />
          ))}
          {previewFixtures.map((f, i) => (
            <PreviewMatchCard
              key={f.fixtureId}
              fixture={f}
              index={upcoming.length + i}
            />
          ))}
        </div>
      )}
      <PastDisclosure count={past.length}>
        {past.map((g, i) => (
          <MatchCard
            key={g.fixtureId}
            match={g}
            detail={matchDetails[g.fixtureId] ?? null}
            index={i}
          />
        ))}
      </PastDisclosure>
    </section>
  );
}
```

- [ ] **Step 3: Fetch `getUpcomingFixtures()` and pass it to both panels**

Change:

```typescript
  const [goals, props, graded, kellySim, matchDetails] = await Promise.all([
    getGoalsPicks(),
    getPropsPicks(),
    getGradedResults(),
    getKellySimResults(),
    getMatchDetails(),
  ]);
```

to:

```typescript
  const [goals, props, graded, kellySim, matchDetails, upcomingFixtures] = await Promise.all([
    getGoalsPicks(),
    getPropsPicks(),
    getGradedResults(),
    getKellySimResults(),
    getMatchDetails(),
    getUpcomingFixtures(),
  ]);
```

Change:

```tsx
        goals={<GoalsPanel goals={goals} matchDetails={matchDetails} />}
        props={<PropsPanel props={props} mostProbable={mostProbable} />}
```

to:

```tsx
        goals={
          <GoalsPanel
            goals={goals}
            matchDetails={matchDetails}
            upcomingFixtures={upcomingFixtures}
          />
        }
        props={
          <PropsPanel
            props={props}
            mostProbable={mostProbable}
            upcomingFixtures={upcomingFixtures}
          />
        }
```

- [ ] **Step 4: Update `PropsPanel.tsx` to include preview fixtures**

Replace the whole file with:

```tsx
import type { PropsPick, MostProbablePick, UpcomingFixture } from "@/lib/data";
import MostProbableStrip from "./MostProbableStrip";
import MatchPropsTable from "./MatchPropsTable";
import PastDisclosure from "./PastDisclosure";
import PreviewMatchCard from "./PreviewMatchCard";

export default function PropsPanel({
  props,
  mostProbable,
  upcomingFixtures,
}: {
  props: PropsPick[];
  mostProbable: MostProbablePick[];
  upcomingFixtures: UpcomingFixture[];
}) {
  const propsByFixture = new Map<string, PropsPick[]>();
  for (const p of props) {
    const arr = propsByFixture.get(p.fixtureId) ?? [];
    arr.push(p);
    propsByFixture.set(p.fixtureId, arr);
  }

  // A fixture's rows all share the same kickoff, so any row's kickoff tells
  // us whether the whole group is upcoming or already played.
  const now = Date.now();
  const groups = [...propsByFixture.entries()];
  const upcomingGroups = groups.filter(([, rows]) => new Date(rows[0].kickoff).getTime() > now);
  const pastGroups = groups.filter(([, rows]) => new Date(rows[0].kickoff).getTime() <= now);
  // Any upcoming fixture without prop rows yet shows as a preview card -
  // once its lineup is confirmed it'll show up in propsByFixture above and
  // drop out of this list automatically.
  const previewFixtures = upcomingFixtures.filter((f) => !propsByFixture.has(f.fixtureId));

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Player shots &amp; shots-on-target</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Well-calibrated in backtesting (gaps within ±0.03). Live profit untested,
        no historical prop-odds archive exists to backtest against. SOT 3+ has no
        underlying data yet, shown as -.
      </p>

      <MostProbableStrip picks={mostProbable} />

      {propsByFixture.size === 0 && previewFixtures.length === 0 ? (
        <p className="text-sm text-neutral-500">No prop predictions logged yet.</p>
      ) : upcomingGroups.length === 0 && previewFixtures.length === 0 ? (
        <p className="text-sm text-neutral-500">No upcoming prop predictions right now.</p>
      ) : (
        <div className="space-y-4">
          {upcomingGroups.map(([fixtureId, rows]) => (
            <MatchPropsTable key={fixtureId} fixtureId={fixtureId} rows={rows} />
          ))}
          {previewFixtures.map((f, i) => (
            <PreviewMatchCard
              key={f.fixtureId}
              fixture={f}
              index={upcomingGroups.length + i}
            />
          ))}
        </div>
      )}
      <PastDisclosure count={pastGroups.length}>
        {pastGroups.map(([fixtureId, rows]) => (
          <MatchPropsTable key={fixtureId} fixtureId={fixtureId} rows={rows} />
        ))}
      </PastDisclosure>
    </section>
  );
}
```

- [ ] **Step 5: Verify**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no output

Run (from `dashboard/`): `npm run build`
Expected: `✓ Compiled successfully`, same route table as before (`/`, `/_not-found`, `/api/notify`, `/api/subscribe`, `/icon.svg`)

- [ ] **Step 6: Commit**

```bash
git add dashboard/app/page.tsx dashboard/components/PropsPanel.tsx
git commit -m "feat: wire upcoming-fixture preview cards into Goals O/U and Player Props"
```

---

## After all tasks: manual verification (not a subagent task)

Once every task above is committed, verify live in the Browser pane against the dev server:

1. Since `data/processed/upcoming_fixtures.json` won't exist in production until the next live-poll cron run writes it, temporarily hardcode a fake array into `getUpcomingFixtures()`'s return in the running dev server (not committed - revert before finishing) covering 2-3 fake fixtures, to visually confirm: preview cards render correctly on both Goals O/U and Player Props, in the right position (after real upcoming predictions, before the past-predictions disclosure), with the pending-analysis line, and disappear correctly if you also add a matching fake entry to `goals`/`props` (simulating a lineup getting confirmed).
2. Confirm the empty-state messages still render correctly when both `upcomingFixtures` and the real data are empty.
3. Once pushed to production, this can't be fully end-to-end verified until the next live-poll run actually writes real fixtures into `upcoming_fixtures.json` - note this to the user rather than claiming full production verification before that happens (same caveat pattern used for `match_detail.jsonl` in the expandable-match-detail feature).
4. Log the shipped feature as a new `.ladder/ladder.md` rung once merged.
