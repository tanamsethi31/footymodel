# Glossary Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 5th "Glossary" tab explaining every term used elsewhere on the dashboard (EV, decimal odds, Model P(O2.5), xG, Kelly criterion, etc.), grouped into 5 sections.

**Architecture:** One new static presentational component (`GlossaryPanel`, no props, no data fetching) plus the same two small wiring edits used when Staking was added as the 4th tab — `DashboardTabs`'s `TABS` array and props grow by one, `page.tsx` passes the new panel in.

**Tech Stack:** Next.js App Router, Tailwind CSS v4 (existing dashboard, no new dependencies).

Full design rationale and final copy: `docs/superpowers/specs/2026-08-29-glossary-page-design.md`.

---

## Task 1: `GlossaryPanel` component

**Files:**
- Create: `dashboard/components/GlossaryPanel.tsx`

- [ ] **Step 1: Create the component with all 5 sections**

```tsx
export default function GlossaryPanel() {
  return (
    <section className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold mb-1">Glossary</h2>
        <p className="text-sm text-neutral-500">
          What the numbers on the other tabs actually mean.
        </p>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          General concepts
        </h3>
        <dl className="space-y-4 text-sm">
          <div>
            <dt className="font-medium">Expected Value (EV)</dt>
            <dd className="text-neutral-500 mt-0.5">
              For a bet with model probability p and decimal odds o: EV = p x o - 1.
              Positive EV means the price pays out more than it should on average,
              given how often the model thinks the outcome actually happens; negative
              EV means the price is worse than fair value even if the outcome is
              likely. Shown as a percentage (+7.3% means staking 1 unit is expected to
              return 1.073 units on average, across many repeats).
            </dd>
          </div>
          <div>
            <dt className="font-medium">Decimal odds</dt>
            <dd className="text-neutral-500 mt-0.5">
              &quot;@ 1.77&quot; means: stake 1 unit, get back 1.77 total if it wins
              (0.77 profit). Implied probability = 1 / odds (1.77 -&gt; 56.5%). Fair
              (breakeven) odds for a given probability p = 1 / p. A market price above
              that is positive EV, below it is negative.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Track Record terms
        </h3>
        <dl className="space-y-4 text-sm">
          <div>
            <dt className="font-medium">Model accuracy</dt>
            <dd className="text-neutral-500 mt-0.5">
              Fraction of graded goals predictions where the model&apos;s Over/Under
              2.5 pick matched the real result, whether or not there was a bet on it.
            </dd>
          </div>
          <div>
            <dt className="font-medium">Bets placed</dt>
            <dd className="text-neutral-500 mt-0.5">
              Count of graded predictions where the model showed positive EV on a
              side at the time it was logged (paper-trade only, no real stakes).
            </dd>
          </div>
          <div>
            <dt className="font-medium">Bet win rate</dt>
            <dd className="text-neutral-500 mt-0.5">Of those bets, the fraction that actually won.</dd>
          </div>
          <div>
            <dt className="font-medium">Cumulative return</dt>
            <dd className="text-neutral-500 mt-0.5">
              Total realized profit/loss across all bets, in stake units (each bet
              assumed 1 unit).
            </dd>
          </div>
          <div>
            <dt className="font-medium">model &#10003; / &#10007;</dt>
            <dd className="text-neutral-500 mt-0.5">
              Whether the model&apos;s Over/Under pick matched the real final score.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Goals O/U terms
        </h3>
        <dl className="space-y-4 text-sm">
          <div>
            <dt className="font-medium">Model P(O2.5)</dt>
            <dd className="text-neutral-500 mt-0.5">
              The model&apos;s probability that the match finishes with over 2.5
              total goals.
            </dd>
          </div>
          <div>
            <dt className="font-medium">xG total</dt>
            <dd className="text-neutral-500 mt-0.5">
              The model&apos;s expected combined goals for both teams (Dixon-Coles
              model blended with the confirmed starting lineups).
            </dd>
          </div>
          <div>
            <dt className="font-medium">Odds O / U</dt>
            <dd className="text-neutral-500 mt-0.5">
              The best available market price for Over 2.5 / Under 2.5, fetched live.
            </dd>
          </div>
          <div>
            <dt className="font-medium">EV Over / Under</dt>
            <dd className="text-neutral-500 mt-0.5">
              See Expected Value above, computed separately for each side.
            </dd>
          </div>
          <div>
            <dt className="font-medium">starters matched</dt>
            <dd className="text-neutral-500 mt-0.5">
              How many of the confirmed starting XI (out of 11 per side) were
              successfully matched to the model&apos;s historical player database. A
              prediction needs at least 8 of 11 matched per side to be logged at all.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Player Props terms
        </h3>
        <dl className="space-y-4 text-sm">
          <div>
            <dt className="font-medium">Shots 1+ / 2+ / 3+</dt>
            <dd className="text-neutral-500 mt-0.5">
              Probability a player registers at least that many total shots in the
              match.
            </dd>
          </div>
          <div>
            <dt className="font-medium">SOT (Shots on Target) 1+ / 2+</dt>
            <dd className="text-neutral-500 mt-0.5">
              Same idea, restricted to shots that were on target. SOT 3+ shows as
              &quot;-&quot; because that specific threshold has no underlying model
              built for it yet, not because of missing data for a particular player.
            </dd>
          </div>
          <div>
            <dt className="font-medium">Most probable bets</dt>
            <dd className="text-neutral-500 mt-0.5">
              The single highest-probability pick across every player, market, and
              threshold combination logged for today&apos;s fixtures.
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
          Staking terms
        </h3>
        <dl className="space-y-4 text-sm">
          <div>
            <dt className="font-medium">Kelly criterion</dt>
            <dd className="text-neutral-500 mt-0.5">
              A formula for how much of your bankroll to stake on a positive-EV bet
              to maximize long-run growth, based on the size of your edge and the
              odds. Full Kelly can be aggressive; &quot;1/4 Kelly&quot; means staking
              a quarter of what full Kelly recommends, trading some growth for much
              less variance.
            </dd>
          </div>
          <div>
            <dt className="font-medium">Flat stake</dt>
            <dd className="text-neutral-500 mt-0.5">
              A fixed 1% of starting bankroll every bet, regardless of edge size. The
              baseline comparison against the Kelly strategies.
            </dd>
          </div>
          <div>
            <dt className="font-medium">median final bankroll</dt>
            <dd className="text-neutral-500 mt-0.5">
              Across 10,000 simulated seasons, the middle outcome, shown as a
              multiple of the starting bankroll (e.g. &quot;5.43x&quot; means the
              bankroll grew to 5.43 times its starting value in the median
              simulation).
            </dd>
          </div>
          <div>
            <dt className="font-medium">Max drawdown</dt>
            <dd className="text-neutral-500 mt-0.5">
              The largest peak-to-trough drop in bankroll within a single simulated
              season, median across all simulations.
            </dd>
          </div>
          <div>
            <dt className="font-medium">Risk of ruin</dt>
            <dd className="text-neutral-500 mt-0.5">
              How often, across all simulations, the bankroll fell to 5% or less of
              its starting value.
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Type-check**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd dashboard
git add components/GlossaryPanel.tsx
git commit -m "Add GlossaryPanel component"
```

---

## Task 2: Wire the Glossary tab into `DashboardTabs` and `page.tsx`

**Files:**
- Modify: `dashboard/components/DashboardTabs.tsx`
- Modify: `dashboard/app/page.tsx`

- [ ] **Step 1: Read both files to confirm their current state**

Run: `cat dashboard/components/DashboardTabs.tsx dashboard/app/page.tsx`

Confirm `DashboardTabs.tsx` still contains:
```tsx
const TABS = ["Track record", "Goals O/U", "Player props", "Staking"];

export default function DashboardTabs({
  trackRecord,
  goals,
  props,
  staking,
}: {
  trackRecord: ReactNode;
  goals: ReactNode;
  props: ReactNode;
  staking: ReactNode;
}) {
  const [active, setActive] = useState(0);
  const panels = [trackRecord, goals, props, staking];
```
and `page.tsx`'s `<DashboardTabs>` call still ends with:
```tsx
        staking={<StakingPanel results={kellySim} />}
      />
```
If either differs (e.g. from other work landing since this plan was written), stop
and report NEEDS_CONTEXT rather than guessing how to adapt the edit.

- [ ] **Step 2: Add the 5th tab to `DashboardTabs.tsx`**

Change:
```tsx
const TABS = ["Track record", "Goals O/U", "Player props", "Staking"];

export default function DashboardTabs({
  trackRecord,
  goals,
  props,
  staking,
}: {
  trackRecord: ReactNode;
  goals: ReactNode;
  props: ReactNode;
  staking: ReactNode;
}) {
  const [active, setActive] = useState(0);
  const panels = [trackRecord, goals, props, staking];
```
to:
```tsx
const TABS = ["Track record", "Goals O/U", "Player props", "Staking", "Glossary"];

export default function DashboardTabs({
  trackRecord,
  goals,
  props,
  staking,
  glossary,
}: {
  trackRecord: ReactNode;
  goals: ReactNode;
  props: ReactNode;
  staking: ReactNode;
  glossary: ReactNode;
}) {
  const [active, setActive] = useState(0);
  const panels = [trackRecord, goals, props, staking, glossary];
```

Nothing else in this file changes — the `w-32` button width, the
`getBoundingClientRect` clip-path measurement, and the transition timing all already
generalize to any number of tabs (confirmed when Staking was added as the 4th tab).

- [ ] **Step 3: Wire it up in `page.tsx`**

Add the import, alongside the other component imports:
```ts
import GlossaryPanel from "@/components/GlossaryPanel";
```

Change the `<DashboardTabs>` call from:
```tsx
      <DashboardTabs
        trackRecord={<TrackRecordPanel graded={graded} />}
        goals={<GoalsPanel goals={goals} />}
        props={<PropsPanel props={props} mostProbable={mostProbable} />}
        staking={<StakingPanel results={kellySim} />}
      />
```
to:
```tsx
      <DashboardTabs
        trackRecord={<TrackRecordPanel graded={graded} />}
        goals={<GoalsPanel goals={goals} />}
        props={<PropsPanel props={props} mostProbable={mostProbable} />}
        staking={<StakingPanel results={kellySim} />}
        glossary={<GlossaryPanel />}
      />
```

- [ ] **Step 4: Type-check**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Build**

Run (from `dashboard/`): `npm run build`
Expected: succeeds, no errors.

- [ ] **Step 6: Verify in the browser**

Start the dashboard locally, confirm: a 5th "Glossary" tab appears in the tab bar
(pill still slides/clips correctly to it — this exercises the same generalization
that made Staking's addition work); clicking it shows all 5 sections (General
concepts, Track Record, Goals O/U, Player Props, Staking terms) with the exact copy
from Task 1; the other 4 tabs still work exactly as before (no regression from the
`TABS`/`panels` array growing by one).

- [ ] **Step 7: Commit**

```bash
cd dashboard
git add components/DashboardTabs.tsx app/page.tsx
git commit -m "Add Glossary tab to the dashboard"
```

- [ ] **Step 8: Push**

```bash
git push origin main
```

Expected: push succeeds; the Vercel auto-deploy (rootDirectory=dashboard, confirmed
working per R046) picks it up automatically.

---

## Plan self-review notes

- **Spec coverage:** all 5 sections with their exact copy ✓ (Task 1), 5th tab wiring
  in both `DashboardTabs.tsx` and `page.tsx` ✓ (Task 2), explicit no-cross-linking /
  no-search scope boundary respected (neither task adds either). Every term listed in
  the design spec's "Content" section has a corresponding `<dt>`/`<dd>` pair in Task
  1's component — checked term-by-term against the spec.
- **Placeholder scan:** none — the full component is written out verbatim in Task 1
  (unlike the spec document, which elided repeated section markup for brevity, this
  plan contains the complete, real file content).
- **Type consistency:** `GlossaryPanel` is a default export with no props, imported as
  `import GlossaryPanel from "@/components/GlossaryPanel"` and used as
  `<GlossaryPanel />` — matches between Task 1 (definition) and Task 2 (usage). The
  `glossary` prop name is consistent between `DashboardTabs`'s type signature, its
  `panels` array, and `page.tsx`'s JSX prop.
