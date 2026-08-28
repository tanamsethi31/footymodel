# Team-Wise Lineup Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split each match card's single 22-player table on the Player Props tab into two team-scoped tabs, so a viewer sees one team's 11 starters at a time instead of both mixed together.

**Architecture:** Pure frontend change to one existing client component (`MatchPropsTable.tsx`). Adds a second piece of local state (`activeTeam`) alongside the existing threshold state (`thresh`); no data-layer, CSV, or Python changes — `team` is already a field on every row this component receives.

**Tech Stack:** Next.js / TypeScript / Tailwind (existing dashboard, no new dependencies).

Full design rationale: `docs/superpowers/specs/2026-08-28-team-lineup-tabs-design.md`.

---

## Task 1: Add team tabs to `MatchPropsTable.tsx`

**Files:**
- Modify: `dashboard/components/MatchPropsTable.tsx`

- [ ] **Step 1: Read the current file to confirm its exact state**

Run: `cat dashboard/components/MatchPropsTable.tsx`

Expected: matches the version below under "Current file" — confirm before editing, since
other dashboard work may have touched this file since this plan was written.

Current file (for reference — this is what Step 2 modifies):

```tsx
"use client";

import { useState } from "react";
import type { PropsPick } from "@/lib/data";
import { formatKickoff, probClass } from "@/lib/format";

const THRESHOLDS = ["1+", "2+", "3+"];

function valueAt(row: PropsPick, stat: "shots" | "sot", idx: number): number | null {
  if (stat === "shots") return [row.pShotsGt05, row.pShotsGt15, row.pShotsGt25][idx];
  return [row.pSotGt05, row.pSotGt15, null][idx]; // no SOT 3+ data exists yet
}

export default function MatchPropsTable({
  fixtureId,
  rows,
}: {
  fixtureId: string;
  rows: PropsPick[];
}) {
  const [thresh, setThresh] = useState(0);
  const [swapping, setSwapping] = useState(false);

  function pick(i: number) {
    if (i === thresh) return;
    setSwapping(true);
    setTimeout(() => {
      setThresh(i);
      setSwapping(false);
    }, 90);
  }

  return (
    <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
      <div className="flex items-baseline justify-between gap-2 flex-wrap mb-3">
        <span className="font-medium">
          {[...new Set(rows.map((r) => r.team))].join(" v ")}
        </span>
        <span className="text-xs text-neutral-500">{formatKickoff(rows[0].kickoff)}</span>
      </div>

      <div className="flex justify-end mb-2">
        <div className="inline-flex bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg p-0.5 gap-0.5">
          {THRESHOLDS.map((t, i) => (
            <button
              key={t}
              onClick={() => pick(i)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors duration-150 active:scale-95 ${
                i === thresh
                  ? "bg-white dark:bg-neutral-100 text-neutral-900"
                  : "text-neutral-500 dark:text-neutral-400"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-neutral-500 border-b border-neutral-200 dark:border-neutral-800">
              <th className="py-1.5 pr-3 font-normal">Player</th>
              <th className="py-1.5 pr-3 font-normal">Shots on Target</th>
              <th className="py-1.5 pr-3 font-normal">Total Shots</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const sot = valueAt(r, "sot", thresh);
              const shots = valueAt(r, "shots", thresh);
              return (
                <tr
                  key={`${fixtureId}-${r.player}`}
                  className="border-b border-neutral-100 dark:border-neutral-900 last:border-0"
                >
                  <td className="py-1.5 pr-3">{r.player}</td>
                  <td
                    className={`py-1.5 pr-3 font-mono transition-[filter,opacity] duration-150 ${probClass(
                      sot
                    )} ${swapping ? "blur-[3px] opacity-50" : ""}`}
                  >
                    {sot === null ? "—" : `${(sot * 100).toFixed(0)}%`}
                  </td>
                  <td
                    className={`py-1.5 pr-3 font-mono transition-[filter,opacity] duration-150 ${probClass(
                      shots
                    )} ${swapping ? "blur-[3px] opacity-50" : ""}`}
                  >
                    {shots === null ? "—" : `${(shots * 100).toFixed(0)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Replace the file with the team-tabbed version**

Write the full file as:

```tsx
"use client";

import { useState } from "react";
import type { PropsPick } from "@/lib/data";
import { formatKickoff, probClass } from "@/lib/format";

const THRESHOLDS = ["1+", "2+", "3+"];

function valueAt(row: PropsPick, stat: "shots" | "sot", idx: number): number | null {
  if (stat === "shots") return [row.pShotsGt05, row.pShotsGt15, row.pShotsGt25][idx];
  return [row.pSotGt05, row.pSotGt15, null][idx]; // no SOT 3+ data exists yet
}

export default function MatchPropsTable({
  fixtureId,
  rows,
}: {
  fixtureId: string;
  rows: PropsPick[];
}) {
  const teams = [...new Set(rows.map((r) => r.team))];
  const [activeTeam, setActiveTeam] = useState(0);
  const [thresh, setThresh] = useState(0);
  const [swapping, setSwapping] = useState(false);

  function pick(i: number) {
    if (i === thresh) return;
    setSwapping(true);
    setTimeout(() => {
      setThresh(i);
      setSwapping(false);
    }, 90);
  }

  const teamRows = rows.filter((r) => r.team === teams[activeTeam]);

  return (
    <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
      <div className="flex items-baseline justify-between gap-2 flex-wrap mb-3">
        <span className="font-medium">{teams.join(" v ")}</span>
        <span className="text-xs text-neutral-500">{formatKickoff(rows[0].kickoff)}</span>
      </div>

      <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
        <div className="inline-flex bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg p-0.5 gap-0.5">
          {teams.map((t, i) => (
            <button
              key={t}
              onClick={() => setActiveTeam(i)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors duration-150 active:scale-95 ${
                i === activeTeam
                  ? "bg-white dark:bg-neutral-100 text-neutral-900"
                  : "text-neutral-500 dark:text-neutral-400"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="inline-flex bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg p-0.5 gap-0.5">
          {THRESHOLDS.map((t, i) => (
            <button
              key={t}
              onClick={() => pick(i)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors duration-150 active:scale-95 ${
                i === thresh
                  ? "bg-white dark:bg-neutral-100 text-neutral-900"
                  : "text-neutral-500 dark:text-neutral-400"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-neutral-500 border-b border-neutral-200 dark:border-neutral-800">
              <th className="py-1.5 pr-3 font-normal">Player</th>
              <th className="py-1.5 pr-3 font-normal">Shots on Target</th>
              <th className="py-1.5 pr-3 font-normal">Total Shots</th>
            </tr>
          </thead>
          <tbody>
            {teamRows.map((r) => {
              const sot = valueAt(r, "sot", thresh);
              const shots = valueAt(r, "shots", thresh);
              return (
                <tr
                  key={`${fixtureId}-${r.player}`}
                  className="border-b border-neutral-100 dark:border-neutral-900 last:border-0"
                >
                  <td className="py-1.5 pr-3">{r.player}</td>
                  <td
                    className={`py-1.5 pr-3 font-mono transition-[filter,opacity] duration-150 ${probClass(
                      sot
                    )} ${swapping ? "blur-[3px] opacity-50" : ""}`}
                  >
                    {sot === null ? "—" : `${(sot * 100).toFixed(0)}%`}
                  </td>
                  <td
                    className={`py-1.5 pr-3 font-mono transition-[filter,opacity] duration-150 ${probClass(
                      shots
                    )} ${swapping ? "blur-[3px] opacity-50" : ""}`}
                  >
                    {shots === null ? "—" : `${(shots * 100).toFixed(0)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

Changes from the current file, precisely:
1. `teams` computed once at the top (was inline inside the header `<span>` before).
2. New `activeTeam` state, defaulting to `0` (first team in row order — the home team,
   since `shots_engine.py` appends home rows before away rows).
3. New `teamRows` — `rows` filtered to `teams[activeTeam]`.
4. Header `<span>` now just joins `teams` (same rendered text as before, `"{home} v
   {away}"` — unchanged visually).
5. The single "flex justify-end" toggle row is replaced by a "flex items-center
   justify-between" row containing **two** toggles side by side: the new team toggle
   (left) and the existing threshold toggle (right, visually and functionally
   unchanged — same `thresh`/`pick`/`swapping` state as before).
6. Table body maps over `teamRows` instead of `rows` — the only change to the table
   itself.

- [ ] **Step 3: Type-check**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Build**

Run (from `dashboard/`): `npm run build`
Expected: succeeds, no errors.

- [ ] **Step 5: Verify in the browser**

Start the dashboard locally (or use the deployed production URL), open the Player Props
tab, and for a match with real data confirm: two team-name segments appear above the
1+/2+/3+ toggle; clicking a team segment swaps the table to that team's ~11 players;
the previously-selected threshold (1+/2+/3+) stays selected across the team switch;
clicking a threshold value still blur-crossfades the visible team's numbers, same as
before.

- [ ] **Step 6: Commit**

```bash
cd dashboard
git add components/MatchPropsTable.tsx
git commit -m "Split match props table into team-wise tabs"
```

- [ ] **Step 7: Push (triggers the GitHub-linked Vercel auto-deploy)**

```bash
git push origin main
```

Expected: push succeeds; the Vercel auto-deploy (rootDirectory=dashboard, confirmed
working per R046) picks it up automatically — no manual `vercel deploy` needed.

---

## Plan self-review notes

- **Spec coverage:** team toggle above threshold toggle ✓, same visual style as the
  existing threshold toggle (not the top-level pill-slide) ✓, threshold state shared
  across team tabs (only one `thresh`/`setThresh`, unchanged) ✓, table scoped to
  `teamRows` ✓, no data/CSV/Python changes ✓, no changes to any other component ✓. All
  spec sections covered by Task 1.
- **Placeholder scan:** none — full file content given for both current and target
  state.
- **Type consistency:** `PropsPick`'s `team` field (already defined in
  `dashboard/lib/data.ts`) is the only new field this task reads from — no new types
  introduced, nothing to drift.
