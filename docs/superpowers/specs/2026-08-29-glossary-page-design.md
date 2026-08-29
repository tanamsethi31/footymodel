# Glossary page (5th tab) — design

Status: approved (R067–R071 in `.ladder/ladder.md`)

## Purpose

A 5th "Glossary" tab explaining every term shown elsewhere on the dashboard (Model
P(O2.5), xG total, EV, decimal odds, Kelly criterion, etc.) — a plain-language
reference for a viewer who doesn't already know what these mean, addressing the
user's direct question earlier this session about what "@1.01" means. No data
dependency; this is static content.

## Structure

Five sections, in this order:

1. **General concepts** — Expected Value and decimal odds, explained once since both
   Goals O/U and Player Props use them identically (R070).
2. **Track Record terms**
3. **Goals O/U terms**
4. **Player Props terms**
5. **Staking terms**

Same visual pattern as every other tab: `<h2>` section title + a `<p>` description,
repeated per term (bold term label, plain-text explanation directly under it) — no
per-term cards, since ~20 terms in individual bordered boxes would be visually
heavier than anywhere else in the dashboard.

## Content (final copy, all five sections)

### General concepts

**Expected Value (EV)** — For a bet with model probability *p* and decimal odds *o*:
EV = p × o − 1. Positive EV means the price pays out more than it should on average,
given how often the model thinks the outcome actually happens; negative EV means the
price is worse than fair value even if the outcome is likely. Shown as a percentage
(+7.3% means staking 1 unit is expected to return 1.073 units on average, across many
repeats).

**Decimal odds** — "@ 1.77" means: stake 1 unit, get back 1.77 total if it wins (0.77
profit). Implied probability = 1 / odds (1.77 → 56.5%). Fair (breakeven) odds for a
given probability *p* = 1 / p — a market price above that is positive EV, below it is
negative.

### Track Record terms

**Model accuracy** — Fraction of graded goals predictions where the model's
Over/Under 2.5 pick matched the real result, whether or not there was a bet on it.

**Bets placed** — Count of graded predictions where the model showed positive EV on a
side at the time it was logged (paper-trade only, no real stakes).

**Bet win rate** — Of those bets, the fraction that actually won.

**Cumulative return** — Total realized profit/loss across all bets, in stake units
(each bet assumed 1 unit).

**model ✓ / ✗** — Whether the model's Over/Under pick matched the real final score.

### Goals O/U terms

**Model P(O2.5)** — The model's probability that the match finishes with over 2.5
total goals.

**xG total** — The model's expected combined goals for both teams (Dixon-Coles model
blended with the confirmed starting lineups).

**Odds O / U** — The best available market price for Over 2.5 / Under 2.5, fetched
live.

**EV Over / Under** — See Expected Value above, computed separately for each side.

**starters matched** — How many of the confirmed starting XI (out of 11 per side)
were successfully matched to the model's historical player database. A prediction
needs at least 8 of 11 matched per side to be logged at all.

### Player Props terms

**Shots 1+ / 2+ / 3+** — Probability a player registers at least that many total
shots in the match.

**SOT (Shots on Target) 1+ / 2+** — Same idea, restricted to shots that were on
target. SOT 3+ shows as "-" because that specific threshold has no underlying model
built for it yet, not because of missing data for a particular player.

**Most probable bets** — The single highest-probability pick across every player,
market, and threshold combination logged for today's fixtures.

### Staking terms

**Kelly criterion** — A formula for how much of your bankroll to stake on a
positive-EV bet to maximize long-run growth, based on the size of your edge and the
odds. Full Kelly can be aggressive; "1/4 Kelly" means staking a quarter of what full
Kelly recommends, trading some growth for much less variance.

**Flat stake** — A fixed 1% of starting bankroll every bet, regardless of edge size —
the baseline comparison against the Kelly strategies.

**median final bankroll** — Across 10,000 simulated seasons, the middle outcome,
shown as a multiple of the starting bankroll (e.g. "5.43x" means the bankroll grew to
5.43 times its starting value in the median simulation).

**Max drawdown** — The largest peak-to-trough drop in bankroll within a single
simulated season, median across all simulations.

**Risk of ruin** — How often, across all simulations, the bankroll fell to 5% or less
of its starting value.

## Component

### `dashboard/components/GlossaryPanel.tsx` (new)

A single static component, no props, following `StakingPanel.tsx`'s pattern (default
export, server component, no `"use client"` needed since there's no interactivity).

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
              (breakeven) odds for a given probability p = 1 / p. a market price above
              that is positive EV, below it is negative.
            </dd>
          </div>
        </dl>
      </div>

      {/* ... one more <div> block per remaining section (Track Record, Goals O/U,
          Player Props, Staking), each with the same <h3> + <dl> structure and the
          exact copy from the "Content" section above - the full text is given
          verbatim in the implementation plan, not repeated here to keep this spec
          from duplicating 2000+ words of copy twice. */}
    </section>
  );
}
```

### `dashboard/components/DashboardTabs.tsx` (modify)

Same pattern as adding the Staking tab: `TABS` grows to 5 entries, one more `ReactNode`
prop (`glossary`) threaded into `panels`. No other change — the `w-32` fixed width and
the `getBoundingClientRect` clip-path measurement both already generalize to any
number of tabs.

### `dashboard/app/page.tsx` (modify)

Import `GlossaryPanel`, add `glossary={<GlossaryPanel />}` to the `<DashboardTabs>`
call. `GlossaryPanel` takes no props, so no data-fetching changes anywhere in
`page.tsx`.

## Explicitly out of scope

- No changes to any other tab's content or the terms already displayed there — this
  only adds an explanatory reference, doesn't change what's shown elsewhere.
- No search/filter within the glossary — five short sections don't need one.
- No linking from a term's usage site (e.g. clicking "xG total" on the Goals tab to
  jump to its glossary entry) — the user asked for a page explaining terms, not
  cross-linked tooltips (that was R068's rejected "inline tooltips" option).
