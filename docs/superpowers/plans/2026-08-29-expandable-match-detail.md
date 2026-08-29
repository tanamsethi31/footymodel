# Expandable Match Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clicking a match card in the dashboard's Goals O/U tab expands it in place to show a team-model vs. lineup-model vs. blended breakdown, a plain-English confidence read, and the actual starting XI for both teams.

**Architecture:** Each live engine already computes starting-XI names and a team/lineup/blended prediction breakdown, then discards everything but the blended numbers before writing `live_recommendations.csv`. A new shared module, `footymodel/live/match_detail.py`, lets all three engines log that extra data to a new side file, `data/processed/match_detail.jsonl` (one self-contained JSON object per line, keyed by `fixture_id` — deliberately NOT more columns on the already-fragile ragged CSV). The dashboard fetches this new file the same way it fetches the CSVs, joins it to each match by `fixture_id`, and a new `MatchCard` client component renders the join result as an expandable accordion.

**Tech Stack:** Python (pandas, existing `footymodel.live` package), Next.js App Router / TypeScript / Tailwind (existing `dashboard/` app).

**Spec:** `docs/superpowers/specs/2026-08-29-expandable-match-detail-design.md`

---

### Task 1: Shared `match_detail` module + its test

**Files:**
- Create: `footymodel/live/match_detail.py`
- Create: `scripts/match_detail_test.py`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the failing test**

```python
# scripts/match_detail_test.py
"""Unit-check for match_detail.py's shared JSONL detail-log helpers, used by
all three live engines (engine.py/rapidapi_engine.py/sofascore_engine.py) to
log starting-XI names and the team-model/lineup-model breakdown that
live_recommendations.csv doesn't carry - see
docs/superpowers/specs/2026-08-29-expandable-match-detail-design.md. Pure/
data-free except for one temp-file write - safe to run in CI.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live import match_detail

# make_detail() shapes one match's detail row from a LineupModel.predict()
# result - the same schema regardless of which engine calls it.
pred = {
    "exp_team": 2.912, "exp_full": 3.204, "exp_blend": 3.058,
    "p_over25_team": 0.583, "p_over25_full": 0.631, "p_over25_blend": 0.606,
}
detail = match_detail.make_detail(1557370, ["Ederson", "Walker"], ["Henderson", "Munoz"], pred)
assert detail == {
    "fixture_id": 1557370,
    "home_starters": ["Ederson", "Walker"],
    "away_starters": ["Henderson", "Munoz"],
    "exp_team": 2.91, "exp_full": 3.2,
    "p_over25_team": 0.583, "p_over25_full": 0.631,
}, detail

# extract_and_log_details() pops "_detail" from each row IN PLACE (so it
# never leaks into the live_recommendations.csv DataFrame) and appends the
# collected details to MATCH_DETAIL_LOG as JSONL.
with tempfile.TemporaryDirectory() as tmp:
    match_detail.MATCH_DETAIL_LOG = Path(tmp) / "match_detail.jsonl"

    rows = [
        {"fixture_id": 1, "home": "A", "_detail": {"fixture_id": 1, "home_starters": ["X"]}},
        {"fixture_id": 2, "home": "B"},  # no "_detail" - e.g. odds fetch failed upstream
    ]
    match_detail.extract_and_log_details(rows)

    assert "_detail" not in rows[0], "detail key must be popped, never left on the CSV row"
    assert rows[0] == {"fixture_id": 1, "home": "A"}
    assert rows[1] == {"fixture_id": 2, "home": "B"}

    lines = match_detail.MATCH_DETAIL_LOG.read_text().strip().splitlines()
    assert len(lines) == 1, "only the row that HAD a _detail should be logged"
    assert json.loads(lines[0]) == {"fixture_id": 1, "home_starters": ["X"]}

    # Never raises, even when every row lacks "_detail" - it's called
    # unconditionally after every poll, confirmed-lineup or not.
    match_detail.extract_and_log_details([{"fixture_id": 3}])

print("match_detail_test: OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/match_detail_test.py`
Expected: `ModuleNotFoundError: No module named 'footymodel.live.match_detail'`

- [ ] **Step 3: Write the module**

```python
# footymodel/live/match_detail.py
"""Shared JSONL side-log for expanded match-detail data (starting XI names,
team-model vs. lineup-model breakdown) that live_recommendations.csv doesn't
carry - see docs/superpowers/specs/2026-08-29-expandable-match-detail-design.md.

Deliberately kept separate from the CSV: live_recommendations.csv's ragged
trailing-column format already caused two bugs this session (R050, R072)
from silently growing optional fields over time. Each line here is a
self-contained JSON object instead, so there's no positional/column-count
ambiguity regardless of which engine writes it.
"""
from __future__ import annotations

import json

from ..data import PROCESSED_DIR

MATCH_DETAIL_LOG = PROCESSED_DIR / "match_detail.jsonl"


def make_detail(fixture_id, home_starters: list[str], away_starters: list[str],
                pred: dict) -> dict:
    """Shape one match's detail row from a LineupModel.predict() result.
    Defined in exactly one place so all three engines log an identical
    schema regardless of their own row-building code."""
    return {
        "fixture_id": fixture_id,
        "home_starters": home_starters,
        "away_starters": away_starters,
        "exp_team": round(pred["exp_team"], 2),
        "exp_full": round(pred["exp_full"], 2),
        "p_over25_team": round(pred["p_over25_team"], 3),
        "p_over25_full": round(pred["p_over25_full"], 3),
    }


def extract_and_log_details(rows: list[dict]) -> None:
    """Pops the private "_detail" key from each row IN PLACE - so it never
    ends up in the live_recommendations.csv DataFrame - and appends the
    collected details to MATCH_DETAIL_LOG as JSONL. Call this AFTER building
    `rows` but BEFORE writing them to the CSV. Never raises: a failure here
    must never look like a lost prediction to the caller, since the actual
    prediction lives entirely in `rows`, independent of this file."""
    details = [r.pop("_detail") for r in rows if "_detail" in r]
    if not details:
        return
    try:
        MATCH_DETAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(MATCH_DETAIL_LOG, "a") as f:
            for d in details:
                f.write(json.dumps(d) + "\n")
    except Exception as e:
        print(f"  ! failed to write match_detail.jsonl (predictions themselves were still logged fine): {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/match_detail_test.py`
Expected: `match_detail_test: OK`

- [ ] **Step 5: Wire into CI**

In `.github/workflows/ci.yml`, add this step after the existing "Grade-results ragged-column parsing" step (keep the same style/indentation as its neighbors):

```yaml
      - name: Match-detail JSONL logging (pure, data-free)
        run: python scripts/match_detail_test.py
```

- [ ] **Step 6: Commit**

```bash
git add footymodel/live/match_detail.py scripts/match_detail_test.py .github/workflows/ci.yml
git commit -m "feat: add shared match_detail.py JSONL logging module"
```

---

### Task 2: Wire `engine.py` (API-Football)

**Files:**
- Modify: `footymodel/live/engine.py`

- [ ] **Step 1: Import the new module**

Add to the import block (after `from . import namematch` at line 25):

```python
from . import match_detail
```

- [ ] **Step 2: Attach `_detail` in `process_fixture()`**

In `process_fixture()`, right before `return row` (currently the last line of the method, after the `if over_odds and under_odds:` block):

```python
        row["_detail"] = match_detail.make_detail(
            fixture_id, home_names, away_names, pred)
        return row
```

- [ ] **Step 3: Extract and log details before the CSV write in `run_once()`**

In `run_once()`, change:

```python
        if new_rows:
            df = pd.DataFrame(new_rows)
```

to:

```python
        match_detail.extract_and_log_details(new_rows)
        if new_rows:
            df = pd.DataFrame(new_rows)
```

- [ ] **Step 4: Verify with the existing dry-run script**

Run: `python scripts/live_dryrun.py`
Expected: `ALL CHECKS PASSED — pipeline plumbing is correct end-to-end.` (this script calls `process_fixture()` directly and only inspects specific keys, so the added `_detail` key doesn't break its assertions — confirm this by eye in the printed `row` dict, which will now include a `_detail: {...}` line)

- [ ] **Step 5: Commit**

```bash
git add footymodel/live/engine.py
git commit -m "feat: log match_detail.jsonl from engine.py"
```

---

### Task 3: Wire `rapidapi_engine.py`

**Files:**
- Modify: `footymodel/live/rapidapi_engine.py`

- [ ] **Step 1: Import the new module**

Add to the import block (after `from . import namematch` at line 36):

```python
from . import match_detail
```

- [ ] **Step 2: Attach `_detail` in `process_fixture()`**

Right before `return row` (currently the last line of the method):

```python
        row["_detail"] = match_detail.make_detail(
            row["fixture_id"], home_starters, away_starters, pred)
        return row
```

(Note: uses `row["fixture_id"]`, not `event_id` — this engine's row uses `f"rapid_{event_id}"` as the fixture id, and the detail file must key on the exact same value the dashboard will see in `live_recommendations.csv`.)

- [ ] **Step 3: Extract and log details before the CSV write in `run_once()`**

Change:

```python
        if new_rows:
            df = pd.DataFrame(new_rows)
```

to:

```python
        match_detail.extract_and_log_details(new_rows)
        if new_rows:
            df = pd.DataFrame(new_rows)
```

- [ ] **Step 4: Verify**

Run: `python -m compileall -q footymodel/live/rapidapi_engine.py`
Expected: no output (clean compile — this engine's real run needs a live `RAPIDAPI_KEY` and remaining monthly budget, so it can't be dry-run locally; a compile check plus the shared module's own test from Task 1 is the available verification)

- [ ] **Step 5: Commit**

```bash
git add footymodel/live/rapidapi_engine.py
git commit -m "feat: log match_detail.jsonl from rapidapi_engine.py"
```

---

### Task 4: Wire `sofascore_engine.py`

**Files:**
- Modify: `footymodel/live/sofascore_engine.py`

- [ ] **Step 1: Import the new module**

Add to the import block (after `from . import namematch` at line 31):

```python
from . import match_detail
```

- [ ] **Step 2: Attach `_detail` in `process_fixture()`**

Right before `return row` (currently the last line of the method):

```python
        row["_detail"] = match_detail.make_detail(
            row["fixture_id"], home_names, away_names, pred)
        return row
```

- [ ] **Step 3: Extract and log details before the CSV write in `run_once()`**

Change:

```python
        if new_rows:
            df = pd.DataFrame(new_rows)
```

to:

```python
        match_detail.extract_and_log_details(new_rows)
        if new_rows:
            df = pd.DataFrame(new_rows)
```

- [ ] **Step 4: Verify**

Run: `python -m compileall -q footymodel/live/sofascore_engine.py`
Expected: no output (clean compile — this engine needs a real Playwright browser session to run end-to-end, not available in this dev environment; compile check + Task 1's test is the available verification)

- [ ] **Step 5: Commit**

```bash
git add footymodel/live/sofascore_engine.py
git commit -m "feat: log match_detail.jsonl from sofascore_engine.py"
```

---

### Task 5: Wire `run_all.py`

**Files:**
- Modify: `footymodel/live/run_all.py`

`run_all.py` reimplements the fetch/process/write loop itself (rather than calling `LiveWatcher.run_once()`), calling `goals.process_fixture()` directly — since Task 2 already made `process_fixture()` attach `_detail` to every row it returns, `goal_row` here already carries it. Only the "pop + log" step needs adding.

- [ ] **Step 1: Import the new module**

Add to the import block (after `from ..data import PROCESSED_DIR` at line 20):

```python
from . import match_detail
```

- [ ] **Step 2: Extract and log details before the CSV write**

Change:

```python
    if goal_rows:
        df = pd.DataFrame(goal_rows)
```

to:

```python
    match_detail.extract_and_log_details(goal_rows)
    if goal_rows:
        df = pd.DataFrame(goal_rows)
```

- [ ] **Step 3: Verify**

Run: `python -m compileall -q footymodel/live/run_all.py`
Expected: no output (clean compile — a full run needs a live `API_FOOTBALL_KEY`; Task 1's test already covers `extract_and_log_details()`'s behavior directly)

- [ ] **Step 4: Commit**

```bash
git add footymodel/live/run_all.py
git commit -m "feat: log match_detail.jsonl from run_all.py"
```

---

### Task 6: Frontend data layer

**Files:**
- Modify: `dashboard/lib/data.ts`

- [ ] **Step 1: Add the `MatchDetail` type**

Add near the other type definitions (after the `GoalsPick` type, before `GradedResult`):

```typescript
export type MatchDetail = {
  fixtureId: string;
  homeStarters: string[];
  awayStarters: string[];
  expTeam: number;
  expFull: number;
  pOver25Team: number;
  pOver25Full: number;
};
```

- [ ] **Step 2: Add a JSONL fetch helper**

Add right after the existing `fetchCsv()` function:

```typescript
async function fetchJsonl(name: string): Promise<Record<string, unknown>[]> {
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
  if (res.status === 404) return []; // file doesn't exist yet (no rows logged)
  if (!res.ok) throw new Error(`Failed to fetch ${name}: ${res.status} ${await res.text()}`);
  const text = await res.text();
  return text
    .split("\n")
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line));
}
```

- [ ] **Step 3: Add `getMatchDetails()`**

Add after `getGoalsPicks()`:

```typescript
export async function getMatchDetails(): Promise<Record<string, MatchDetail>> {
  const rows = await fetchJsonl("match_detail.jsonl");
  const byFixtureId: Record<string, MatchDetail> = {};
  for (const r of rows) {
    const fixtureId = String(r.fixture_id);
    byFixtureId[fixtureId] = {
      fixtureId,
      homeStarters: (r.home_starters as string[]) ?? [],
      awayStarters: (r.away_starters as string[]) ?? [],
      expTeam: Number(r.exp_team),
      expFull: Number(r.exp_full),
      pOver25Team: Number(r.p_over25_team),
      pOver25Full: Number(r.p_over25_full),
    };
  }
  return byFixtureId;
}
```

- [ ] **Step 4: Verify**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no output (clean type-check)

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/data.ts
git commit -m "feat: fetch and join match_detail.jsonl in the dashboard data layer"
```

---

### Task 7: `MatchCard` component

**Files:**
- Create: `dashboard/components/MatchCard.tsx`

- [ ] **Step 1: Write the component**

```tsx
// dashboard/components/MatchCard.tsx
"use client";

import { useState } from "react";
import type { GoalsPick, MatchDetail } from "@/lib/data";
import { formatKickoff, pct, odds, EvBadge, SOURCE_LABEL } from "@/lib/format";

const CONFIDENCE_THRESHOLD = 0.05;

function confidenceLine(detail: MatchDetail): string {
  const gap = Math.abs(detail.pOver25Team - detail.pOver25Full);
  return gap < CONFIDENCE_THRESHOLD
    ? "Team and lineup models agree closely."
    : "Team and lineup models diverge.";
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className={`w-4 h-4 shrink-0 text-neutral-400 transition-transform duration-150 ${
        open ? "rotate-180" : ""
      }`}
      aria-hidden="true"
    >
      <path
        d="M6 9l6 6 6-6"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function MatchCard({
  match,
  detail,
  index,
}: {
  match: GoalsPick;
  detail: MatchDetail | null;
  index: number;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => setOpen((o) => !o)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setOpen((o) => !o);
        }
      }}
      className="animate-stagger-in rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 transition-transform duration-150 hover:-translate-y-0.5 cursor-pointer"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className="font-medium flex items-center gap-2">
          <Chevron open={open} />
          {match.home} v {match.away}
        </span>
        <span className="text-xs text-neutral-500">{formatKickoff(match.kickoff)}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div>
          <div className="text-neutral-500 text-xs">Model P(O2.5)</div>
          <div className="font-mono">{pct(match.modelPOver25)}</div>
        </div>
        <div>
          <div className="text-neutral-500 text-xs">xG total</div>
          <div className="font-mono">{match.expTotalGoals.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-neutral-500 text-xs">Odds O / U</div>
          <div className="font-mono">
            {odds(match.oddsOver25)} / {odds(match.oddsUnder25)}
          </div>
        </div>
        <div>
          <div className="text-neutral-500 text-xs">EV Over / Under</div>
          <div className="flex gap-2">
            <EvBadge ev={match.evOver25} />
            <EvBadge ev={match.evUnder25} />
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs text-neutral-400">
        <span>
          starters matched {match.nHomeMatched}/{match.nAwayMatched}
        </span>
        <span>·</span>
        <span>{SOURCE_LABEL[match.source ?? ""] ?? match.source}</span>
      </div>

      {open && (
        <div
          className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-800 text-sm"
          onClick={(e) => e.stopPropagation()}
        >
          {detail === null ? (
            <p className="text-xs text-neutral-400">
              Detailed breakdown not available for this prediction.
            </p>
          ) : (
            <>
              <div className="text-neutral-500 text-xs mb-2">Model breakdown</div>
              <div className="grid grid-cols-3 gap-3 font-mono text-xs mb-3">
                <div>
                  <div className="text-neutral-400">Team model</div>
                  <div>
                    {detail.expTeam.toFixed(2)} xG · {pct(detail.pOver25Team)}
                  </div>
                </div>
                <div>
                  <div className="text-neutral-400">Lineup model</div>
                  <div>
                    {detail.expFull.toFixed(2)} xG · {pct(detail.pOver25Full)}
                  </div>
                </div>
                <div>
                  <div className="text-neutral-400">Blended</div>
                  <div>
                    {match.expTotalGoals.toFixed(2)} xG · {pct(match.modelPOver25)}
                  </div>
                </div>
              </div>
              <p className="text-xs text-neutral-500 mb-3">{confidenceLine(detail)}</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-neutral-500 text-xs mb-1">{match.home}</div>
                  <ul className="text-xs text-neutral-600 dark:text-neutral-400 space-y-0.5">
                    {detail.homeStarters.map((n) => (
                      <li key={n}>{n}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="text-neutral-500 text-xs mb-1">{match.away}</div>
                  <ul className="text-xs text-neutral-600 dark:text-neutral-400 space-y-0.5">
                    {detail.awayStarters.map((n) => (
                      <li key={n}>{n}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no output. This will report unused-import-style errors if `MatchCard` isn't wired into `page.tsx` yet — that happens in Task 8, so a clean pass here only confirms the component itself type-checks in isolation (no import errors, correct prop types against `GoalsPick`/`MatchDetail`).

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/MatchCard.tsx
git commit -m "feat: add MatchCard expandable component"
```

---

### Task 8: Wire `MatchCard` into the Goals O/U tab

**Files:**
- Modify: `dashboard/app/page.tsx`

- [ ] **Step 1: Update imports**

Change:

```typescript
import {
  getGoalsPicks,
  getPropsPicks,
  getGradedResults,
  getMostProbablePicks,
  getKellySimResults,
  type GoalsPick,
  type GradedResult,
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
  type GoalsPick,
  type GradedResult,
  type MatchDetail,
} from "@/lib/data";
```

Add, after the other component imports:

```typescript
import MatchCard from "@/components/MatchCard";
```

- [ ] **Step 2: Replace `GoalsPanel`'s inline row with `MatchCard`**

Replace the whole `GoalsPanel` function (lines 124-187) with:

```tsx
function GoalsPanel({
  goals,
  matchDetails,
}: {
  goals: GoalsPick[];
  matchDetails: Record<string, MatchDetail>;
}) {
  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Goals: Over/Under 2.5</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Confirmed-lineup model, pooled t=3.04 backtested (individually
        significant on the Premier League alone, t=2.23).
      </p>
      {goals.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No predictions logged yet. Check back once a fixture&apos;s lineup
          is confirmed pre-kickoff.
        </p>
      ) : (
        <div className="space-y-3">
          {goals.map((g, i) => (
            <MatchCard
              key={g.fixtureId}
              match={g}
              detail={matchDetails[g.fixtureId] ?? null}
              index={i}
            />
          ))}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 3: Fetch `getMatchDetails()` and pass it down**

Change:

```typescript
  const [goals, props, graded, kellySim] = await Promise.all([
    getGoalsPicks(),
    getPropsPicks(),
    getGradedResults(),
    getKellySimResults(),
  ]);
```

to:

```typescript
  const [goals, props, graded, kellySim, matchDetails] = await Promise.all([
    getGoalsPicks(),
    getPropsPicks(),
    getGradedResults(),
    getKellySimResults(),
    getMatchDetails(),
  ]);
```

Change:

```tsx
        goals={<GoalsPanel goals={goals} />}
```

to:

```tsx
        goals={<GoalsPanel goals={goals} matchDetails={matchDetails} />}
```

- [ ] **Step 4: Verify**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no output

Run (from `dashboard/`): `npm run build`
Expected: `✓ Compiled successfully`, ending with the same route table as before (`/`, `/_not-found`, `/api/notify`, `/api/subscribe`, `/icon.svg`) — no new routes, this only changes what `/` renders.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/page.tsx
git commit -m "feat: wire MatchCard into the Goals O/U tab"
```

---

## After all tasks: manual verification (not a subagent task)

Once every task above is committed, verify live in the Browser pane against the dev server, same process used for every other frontend change this session:

1. Load the dashboard, open the Goals O/U tab, click a match card — confirm it expands, the chevron rotates, and (since every existing `live_recommendations.csv` row predates this feature and has no `match_detail.jsonl` entry) the fallback line "Detailed breakdown not available for this prediction." renders correctly with no layout break.
2. Click the same card again — confirm it collapses.
3. To visually confirm the **populated** state (model breakdown, confidence line, starting XI) actually renders correctly, temporarily hardcode one fake entry into `getMatchDetails()`'s returned object for a real `fixtureId` already in the data (do this directly in the running dev server's file, do NOT commit it) — verify the layout, then revert the temporary change before moving on.
4. True end-to-end confirmation that a live engine actually writes a real `match_detail.jsonl` entry in production will only happen once the next confirmed-lineup prediction lands via the cron poller — note this to the user rather than claiming it's been production-verified before that happens (same caveat pattern used for R072's re-graded fixture).
5. Log the shipped feature as a new `.ladder/ladder.md` rung once merged.
