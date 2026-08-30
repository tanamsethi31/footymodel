# Dashboard Polish Round Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship three small, independent dashboard polish fixes: sort upcoming matches by soonest-kickoff-first on both prediction tabs, add blue left-border accent bars to Glossary entries, and show a "last run" timestamp on the Staking tab.

**Architecture:** Items 1-2 are pure frontend array-sort additions in already-existing filter logic. Item 3 is a one-line backend timestamp stamp plus a matching frontend field, threaded through the same GitHub-Contents-API CSV read path every other data file already uses. No new files, no new dependencies, no schema migrations beyond one new optional CSV column.

**Tech Stack:** Next.js App Router, TypeScript, Tailwind CSS (dashboard/); Python + pandas (scripts/kelly_simulation.py).

See spec: `docs/superpowers/specs/2026-08-30-dashboard-polish-round-design.md`

---

### Task 1: Sort Goals O/U upcoming matches by kickoff

**Files:**
- Modify: `dashboard/app/page.tsx` (the `GoalsPanel` function, around lines 143-152)

- [ ] **Step 1: Add ascending-kickoff sorts to `upcoming` and `previewFixtures`**

In `dashboard/app/page.tsx`, find this block inside `GoalsPanel`:

```tsx
  const now = Date.now();
  const upcoming = goals.filter((g) => new Date(g.kickoff).getTime() > now);
  const past = goals.filter((g) => new Date(g.kickoff).getTime() <= now);
  const predictedFixtureIds = new Set(goals.map((g) => g.fixtureId));
  const previewFixtures = upcomingFixtures.filter(
    (f) => !predictedFixtureIds.has(f.fixtureId) && new Date(f.kickoff).getTime() > now
  );
```

Replace it with:

```tsx
  const now = Date.now();
  const byKickoffAsc = (a: { kickoff: string }, b: { kickoff: string }) =>
    new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime();
  const upcoming = goals
    .filter((g) => new Date(g.kickoff).getTime() > now)
    .sort(byKickoffAsc);
  const past = goals.filter((g) => new Date(g.kickoff).getTime() <= now);
  const predictedFixtureIds = new Set(goals.map((g) => g.fixtureId));
  const previewFixtures = upcomingFixtures
    .filter((f) => !predictedFixtureIds.has(f.fixtureId) && new Date(f.kickoff).getTime() > now)
    .sort(byKickoffAsc);
```

`past` is untouched — it keeps the descending (most-recent-first) order it already gets from `getGoalsPicks()`.

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors (the shared `byKickoffAsc` helper's `{ kickoff: string }` parameter type is structurally compatible with both `GoalsPick` and `UpcomingFixture`, since both have a `kickoff: string` field).

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/page.tsx
git commit -m "fix: sort Goals O/U upcoming matches by soonest kickoff first"
```

---

### Task 2: Sort Player Props upcoming matches by kickoff

**Files:**
- Modify: `dashboard/components/PropsPanel.tsx` (lines ~25-34)

- [ ] **Step 1: Add ascending-kickoff sorts to `upcomingGroups` and `previewFixtures`**

In `dashboard/components/PropsPanel.tsx`, find:

```tsx
  const now = Date.now();
  const groups = [...propsByFixture.entries()];
  const upcomingGroups = groups.filter(([, rows]) => new Date(rows[0].kickoff).getTime() > now);
  const pastGroups = groups.filter(([, rows]) => new Date(rows[0].kickoff).getTime() <= now);
  const previewFixtures = upcomingFixtures.filter(
    (f) => !propsByFixture.has(f.fixtureId) && new Date(f.kickoff).getTime() > now
  );
```

Replace it with:

```tsx
  const now = Date.now();
  const groups = [...propsByFixture.entries()];
  const upcomingGroups = groups
    .filter(([, rows]) => new Date(rows[0].kickoff).getTime() > now)
    .sort((a, b) => new Date(a[1][0].kickoff).getTime() - new Date(b[1][0].kickoff).getTime());
  const pastGroups = groups.filter(([, rows]) => new Date(rows[0].kickoff).getTime() <= now);
  const previewFixtures = upcomingFixtures
    .filter((f) => !propsByFixture.has(f.fixtureId) && new Date(f.kickoff).getTime() > now)
    .sort((a, b) => new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime());
```

(`upcomingGroups` entries are `[fixtureId, PropsPick[]]` tuples, so the sort compares `a[1][0].kickoff` — the first row's kickoff — same value the filter above it already reads.)

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/PropsPanel.tsx
git commit -m "fix: sort Player Props upcoming matches by soonest kickoff first"
```

---

### Task 3: Glossary blue-accent bars

**Files:**
- Modify: `dashboard/components/GlossaryPanel.tsx`

- [ ] **Step 1: Add a left-border accent to every term wrapper**

Every glossary entry in `dashboard/components/GlossaryPanel.tsx` follows this exact pattern (confirmed identical indentation across all ~16 entries):

```tsx
          <div>
            <dt className="font-medium">
```

Replace **every** occurrence of that pattern with:

```tsx
          <div className="border-l-2 border-blue-500 dark:border-blue-400 pl-3">
            <dt className="font-medium">
```

This is a single find-and-replace-all across the file — do not touch the section-header `<div>`s (the ones right before an `<h3>`, e.g. `<h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">`), since those have different indentation (6 spaces, not 10) and aren't part of this pattern.

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors (this is a pure JSX className change, no type surface affected).

- [ ] **Step 3: Visually verify in the dev server**

Run: `cd dashboard && npm run dev`, open the Glossary tab.
Expected: every term (e.g. "Expected Value (EV)", "Kelly criterion") has a thin blue vertical bar to its left, in both light and dark mode (toggle OS/browser dark mode to check). Section headers ("General concepts", "Track Record terms", etc.) do NOT have a bar. Stop the dev server after checking (`Ctrl+C`).

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/GlossaryPanel.tsx
git commit -m "style: add blue left-border accent to Glossary entries"
```

---

### Task 4: Stamp a generation timestamp into kelly_simulation.csv

**Files:**
- Modify: `scripts/kelly_simulation.py`

- [ ] **Step 1: Import `datetime` and stamp the DataFrame before writing**

In `scripts/kelly_simulation.py`, find the import block:

```python
import argparse
import sys
from pathlib import Path
```

Replace with:

```python
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
```

Then find:

```python
    result = sweep(bets, n_trials=args.n_trials, start_bankroll=args.start_bankroll,
                   seed=args.seed)
    result.to_csv(SIM_OUTPUT_PATH, index=False)
```

Replace with:

```python
    result = sweep(bets, n_trials=args.n_trials, start_bankroll=args.start_bankroll,
                   seed=args.seed)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result.to_csv(SIM_OUTPUT_PATH, index=False)
```

- [ ] **Step 2: Run the script and confirm the new column**

Run: `python scripts/kelly_simulation.py`
Expected: same console output as before (strategy table), and `data/processed/kelly_simulation.csv`'s header row now ends in `,generated_at`, with every data row carrying the same UTC ISO timestamp from this run.

Then run: `git diff --stat data/processed/kelly_simulation.csv`
Expected: only this one file changed. Run `git diff data/processed/kelly_simulation.csv` and confirm every numeric column's values are unchanged from before (same seed=0 default, so the simulation itself is deterministic) — the only diff should be the new `generated_at` column.

- [ ] **Step 3: Commit**

```bash
git add scripts/kelly_simulation.py data/processed/kelly_simulation.csv
git commit -m "feat: stamp kelly_simulation.csv with a generation timestamp"
```

---

### Task 5: Thread `generatedAt` through the dashboard's data layer

**Files:**
- Modify: `dashboard/lib/data.ts`

- [ ] **Step 1: Add `generatedAt` to the `KellySimResult` type**

Find:

```ts
export type KellySimResult = {
  strategy: string;
  kellyMult: number | null;
  nTrials: number;
  nBets: number;
  startBankroll: number;
  medianFinalBankroll: number;
  p5FinalBankroll: number;
  p95FinalBankroll: number;
  medianMaxDrawdown: number;
  ruinProbability: number;
};
```

Replace with:

```ts
export type KellySimResult = {
  strategy: string;
  kellyMult: number | null;
  nTrials: number;
  nBets: number;
  startBankroll: number;
  medianFinalBankroll: number;
  p5FinalBankroll: number;
  p95FinalBankroll: number;
  medianMaxDrawdown: number;
  ruinProbability: number;
  generatedAt: string | null;
};
```

- [ ] **Step 2: Parse the new column in `getKellySimResults()`**

Find:

```ts
export async function getKellySimResults(): Promise<KellySimResult[]> {
  const rows = await fetchCsv("kelly_simulation.csv");
  return rows
    .map((r) => ({
      strategy: r.strategy,
      kellyMult: num(r.kelly_mult),
      nTrials: num(r.n_trials) ?? 0,
      nBets: num(r.n_bets) ?? 0,
      startBankroll: num(r.start_bankroll) ?? 100,
      medianFinalBankroll: num(r.median_final_bankroll) ?? 0,
      p5FinalBankroll: num(r.p5_final_bankroll) ?? 0,
      p95FinalBankroll: num(r.p95_final_bankroll) ?? 0,
      medianMaxDrawdown: num(r.median_max_drawdown) ?? 0,
      ruinProbability: num(r.ruin_probability) ?? 0,
    }))
    .filter((r) => r.strategy)
    .sort((a, b) => (a.kellyMult ?? -1) - (b.kellyMult ?? -1));
}
```

Replace with:

```ts
export async function getKellySimResults(): Promise<KellySimResult[]> {
  const rows = await fetchCsv("kelly_simulation.csv");
  return rows
    .map((r) => ({
      strategy: r.strategy,
      kellyMult: num(r.kelly_mult),
      nTrials: num(r.n_trials) ?? 0,
      nBets: num(r.n_bets) ?? 0,
      startBankroll: num(r.start_bankroll) ?? 100,
      medianFinalBankroll: num(r.median_final_bankroll) ?? 0,
      p5FinalBankroll: num(r.p5_final_bankroll) ?? 0,
      p95FinalBankroll: num(r.p95_final_bankroll) ?? 0,
      medianMaxDrawdown: num(r.median_max_drawdown) ?? 0,
      ruinProbability: num(r.ruin_probability) ?? 0,
      generatedAt: r.generated_at ?? null,
    }))
    .filter((r) => r.strategy)
    .sort((a, b) => (a.kellyMult ?? -1) - (b.kellyMult ?? -1));
}
```

(`r.generated_at` comes back `undefined` for a CSV row with no such column — `?? null` normalizes that to `null` explicitly, matching the type.)

- [ ] **Step 3: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add dashboard/lib/data.ts
git commit -m "feat: parse generatedAt from kelly_simulation.csv"
```

---

### Task 6: Show the "last run" line on the Staking tab

**Files:**
- Modify: `dashboard/components/StakingPanel.tsx`

- [ ] **Step 1: Import `formatKickoff` and split the subtitle so a conditional line can follow it**

Find:

```tsx
import type { KellySimResult } from "@/lib/data";
```

Replace with:

```tsx
import type { KellySimResult } from "@/lib/data";
import { formatKickoff } from "@/lib/format";
```

Find:

```tsx
      <p className="text-sm text-neutral-500 mb-5">
        Monte Carlo over the {results[0].nBets} backtested E0 O/U 2.5 value bets,{" "}
        {results[0].nTrials.toLocaleString()} simulated seasons per strategy. Downstream
        risk-sizing analysis only. Doesn&apos;t affect the model&apos;s predictions or
        edge. &quot;Ruin&quot; means bankroll fell to 5% of its starting value.
      </p>
```

Replace with:

```tsx
      <p className="text-sm text-neutral-500 mb-1">
        Monte Carlo over the {results[0].nBets} backtested E0 O/U 2.5 value bets,{" "}
        {results[0].nTrials.toLocaleString()} simulated seasons per strategy. Downstream
        risk-sizing analysis only. Doesn&apos;t affect the model&apos;s predictions or
        edge. &quot;Ruin&quot; means bankroll fell to 5% of its starting value.
      </p>
      {results[0].generatedAt && (
        <p className="text-xs text-neutral-400 mb-5">
          Last run: {formatKickoff(results[0].generatedAt)}
        </p>
      )}
```

Note the subtitle's `mb-5` moved down to the new conditional line (`mb-1` on the subtitle now) so the spacing before the results grid stays the same whether or not the line renders — if `generatedAt` is `null` (an old CSV with no such column), nothing extra renders and the `mb-1` alone leaves a slightly tighter gap, which is an acceptable fallback for data that predates this feature.

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Verify in the dev server**

Since Task 4 already regenerated a real `data/processed/kelly_simulation.csv` with a `generated_at` column, and that file is read live from GitHub (not from the local filesystem) by `getKellySimResults()`, the dev server won't see the new column until Task 4's commit is pushed. To verify locally right now:

1. Run: `cd dashboard && npm run dev`, open the Staking tab, and confirm it renders exactly as before (no crash, no "Last run" line yet) — this proves the `generatedAt: null` fallback path works against the current production data.
2. Temporarily edit `dashboard/lib/data.ts`'s `getKellySimResults()` to hardcode `generatedAt: "2026-08-30T12:00:00Z"` in place of `r.generated_at ?? null` for this check only, save, and confirm the Staking tab now shows "Last run: Sun 30 Aug, 17:30 IST" under the subtitle.
3. Revert that temporary edit (`git diff dashboard/lib/data.ts` should show no changes afterward) and stop the dev server (`Ctrl+C`).

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/StakingPanel.tsx
git commit -m "feat: show Kelly simulation's last-run timestamp on the Staking tab"
```

---

## Post-plan verification

Once Tasks 4-6 are pushed to `origin/main` (so Vercel picks up both the new CSV and the new frontend code), confirm live in production that the Staking tab shows a real "Last run" line matching the timestamp in the pushed `kelly_simulation.csv`, and that Goals O/U / Player Props both show their nearest-kickoff match first.
