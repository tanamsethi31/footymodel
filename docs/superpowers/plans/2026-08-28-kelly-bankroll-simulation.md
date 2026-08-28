# Kelly Bankroll Monte Carlo Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Monte Carlo simulator that sweeps Kelly staking fractions over the already-backtested E0 O/U 2.5 value bets, reports risk-of-ruin/drawdown/growth per fraction, and surfaces the results as a new "Staking" tab on the dashboard.

**Architecture:** A pure Python engine (`footymodel/simulate.py`) reads the existing walk-forward backtest evals, filters to positive-EV E0 O/U 2.5 bets, and runs `n_trials` parametric Monte Carlo simulations per staking strategy (reusing `staking.py` unchanged). A thin CLI script writes the summary to `data/processed/kelly_simulation.csv` (same tracked-CSV pattern as `graded_results.csv`). The Next.js dashboard reads that CSV through the existing GitHub Contents API fetch path and renders one stat card per strategy in a new 4th tab.

**Tech Stack:** Python (numpy, pandas — both already dependencies), TypeScript/Next.js (existing dashboard, no new npm packages).

Full design rationale: `docs/superpowers/specs/2026-08-28-kelly-bankroll-simulation-design.md`.

---

## Task 1: `footymodel/simulate.py` — value-bet filtering

**Files:**
- Create: `footymodel/simulate.py`
- Create: `scripts/kelly_simulation_test.py`

- [ ] **Step 1: Write the failing test**

Create `scripts/kelly_simulation_test.py`:

```python
"""Unit-checks for the Kelly bankroll Monte Carlo simulator
(footymodel/simulate.py). Pure/data-free - builds tiny synthetic bet sets
inline, never reads evals_main.parquet - safe to run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.simulate import filter_value_bets

# --- filter_value_bets -------------------------------------------------
raw = pd.DataFrame([
    # league, market, model_p, odds_close -> edge = p*odds-1
    {"date": "2024-01-03", "league": "E0", "market": "over25", "model_p": 0.60, "odds_close": 2.00},  # edge=0.20, KEEP
    {"date": "2024-01-01", "league": "E0", "market": "under25", "model_p": 0.55, "odds_close": 1.90},  # edge=0.045, DROP (below 0.05 threshold)
    {"date": "2024-01-02", "league": "E0", "market": "home", "model_p": 0.70, "odds_close": 2.00},     # edge=0.40, DROP (wrong market)
    {"date": "2024-01-04", "league": "D1", "market": "over25", "model_p": 0.70, "odds_close": 2.00},   # edge=0.40, DROP (wrong league)
])

result = filter_value_bets(raw, league="E0", markets=("over25", "under25"), edge_threshold=0.05)
assert len(result) == 1, f"expected 1 value bet, got {len(result)}"
assert result.iloc[0]["market"] == "over25"
assert list(result.columns) == ["date", "market", "model_p", "odds_close"]

# Chronological sort check - dates in the raw frame are out of order.
raw2 = pd.DataFrame([
    {"date": "2024-03-01", "league": "E0", "market": "over25", "model_p": 0.60, "odds_close": 2.00},
    {"date": "2024-01-01", "league": "E0", "market": "over25", "model_p": 0.60, "odds_close": 2.00},
    {"date": "2024-02-01", "league": "E0", "market": "over25", "model_p": 0.60, "odds_close": 2.00},
])
sorted_result = filter_value_bets(raw2, league="E0", edge_threshold=0.05)
assert list(sorted_result["date"]) == ["2024-01-01", "2024-02-01", "2024-03-01"]

print("kelly_simulation_test: filter_value_bets OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/kelly_simulation_test.py`
Expected: `ModuleNotFoundError: No module named 'footymodel.simulate'`

- [ ] **Step 3: Write minimal implementation**

Create `footymodel/simulate.py`:

```python
"""Kelly-fraction bankroll Monte Carlo simulator.

Takes the walk-forward backtest's already-proven E0 O/U 2.5 edge as given and
answers a downstream question: at what Kelly fraction is staking actually
safe, in terms of risk of ruin, drawdown, and bankroll growth? Does NOT touch
model accuracy/calibration or search for new edge - see
docs/superpowers/specs/2026-08-28-kelly-bankroll-simulation-design.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import PROCESSED_DIR
from .staking import recommended_stake

EVALS_PATH = PROCESSED_DIR / "evals_main.parquet"
SIM_OUTPUT_PATH = PROCESSED_DIR / "kelly_simulation.csv"

DEFAULT_EDGE_THRESHOLD = 0.05  # matches backtest.py / recommend.py's value-bet gate
RUIN_FLOOR_FRACTION = 0.05     # "ruined" = bankroll <= 5% of start_bankroll

# (label, kelly_mult) - kelly_mult=None means flat (fixed 1-unit) staking.
STRATEGIES = [
    ("flat", None),
    ("kelly-0.125", 0.125),
    ("kelly-0.25", 0.25),
    ("kelly-0.5", 0.5),
    ("kelly-1.0", 1.0),
]


def filter_value_bets(df: pd.DataFrame, league: str = "E0",
                       markets: tuple[str, ...] = ("over25", "under25"),
                       edge_threshold: float = DEFAULT_EDGE_THRESHOLD) -> pd.DataFrame:
    """Filter evals rows to positive-EV bets, sorted chronologically.

    `df` needs columns: date, league, market, model_p, odds_close.
    """
    sub = df[(df["league"] == league) & (df["market"].isin(markets))].copy()
    sub["edge"] = sub["model_p"] * sub["odds_close"] - 1.0
    sub = sub[sub["edge"] > edge_threshold]
    sub = sub.sort_values("date").reset_index(drop=True)
    return sub[["date", "market", "model_p", "odds_close"]]


def load_value_bets(league: str = "E0", markets: tuple[str, ...] = ("over25", "under25"),
                     edge_threshold: float = DEFAULT_EDGE_THRESHOLD) -> pd.DataFrame:
    """Read evals_main.parquet and filter to positive-EV bets. See filter_value_bets."""
    df = pd.read_parquet(EVALS_PATH)
    return filter_value_bets(df, league=league, markets=markets, edge_threshold=edge_threshold)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/kelly_simulation_test.py`
Expected: `kelly_simulation_test: filter_value_bets OK`

- [ ] **Step 5: Commit**

```bash
git add footymodel/simulate.py scripts/kelly_simulation_test.py
git commit -m "Add value-bet filtering for the Kelly bankroll simulator"
```

---

## Task 2: `footymodel/simulate.py` — `simulate_bankroll()`

**Files:**
- Modify: `footymodel/simulate.py`
- Modify: `scripts/kelly_simulation_test.py`

- [ ] **Step 1: Write the failing test**

Append to `scripts/kelly_simulation_test.py` (before the final `print` line, replace that
line with the new tests followed by a new final print):

```python
# --- simulate_bankroll ---------------------------------------------------
from footymodel.simulate import simulate_bankroll
from footymodel.staking import recommended_stake

# Integration check: the simulator's kelly staking must match staking.py's
# recommended_stake() exactly, not a reimplementation, on a single bet.
one_bet = pd.DataFrame([
    {"date": "2024-01-01", "market": "over25", "model_p": 0.55, "odds_close": 2.00},
])
result = simulate_bankroll(one_bet, kelly_mult=0.25, n_trials=1, start_bankroll=100.0,
                           max_fraction=0.02, seed=42)
expected_stake = recommended_stake(100.0, 0.55, 2.00, kelly_mult=0.25, max_fraction=0.02)
# With a single bet, final_bankroll is start_bankroll +/- the stake's payout/loss -
# reconstruct which happened and confirm it matches the direct staking.py call.
final = result["final_bankroll"][0]
win_final = 100.0 + expected_stake * (2.00 - 1.0)
lose_final = 100.0 - expected_stake
assert abs(final - win_final) < 1e-9 or abs(final - lose_final) < 1e-9, (
    f"final_bankroll {final} doesn't match either win ({win_final}) or lose ({lose_final}) "
    f"outcome using staking.py's own stake size {expected_stake}"
)

# Ruin floor: flat staking on an all-losses bet set must ruin every trial
# (bankroll walked all the way down through the 5%-of-start floor).
losing_bets = pd.DataFrame([
    {"date": f"2024-01-{i:02d}", "market": "over25", "model_p": 0.0, "odds_close": 2.00}
    for i in range(1, 21)
])
result = simulate_bankroll(losing_bets, kelly_mult=None, n_trials=50, start_bankroll=100.0, seed=1)
assert result["ruined"].all(), "flat staking on 20 guaranteed losses should always ruin"
assert (result["final_bankroll"] <= 5.0).all(), "ruined trials should be at/below the 5% floor"

# Guaranteed wins never ruin, for either strategy.
winning_bets = pd.DataFrame([
    {"date": f"2024-01-{i:02d}", "market": "over25", "model_p": 1.0, "odds_close": 2.00}
    for i in range(1, 11)
])
flat_result = simulate_bankroll(winning_bets, kelly_mult=None, n_trials=20, start_bankroll=100.0, seed=2)
kelly_result = simulate_bankroll(winning_bets, kelly_mult=1.0, n_trials=20, start_bankroll=100.0, seed=2)
assert not flat_result["ruined"].any()
assert not kelly_result["ruined"].any()
assert (flat_result["final_bankroll"] > 100.0).all()
assert (kelly_result["final_bankroll"] > 100.0).all()

# Higher kelly_mult -> higher variance, on a repeated positive-edge bet with
# a thin enough edge that neither multiplier hits the max_fraction cap
# (p=0.55, odds=2.0 -> edge=0.10, full-Kelly fraction=0.10 - use a generous
# max_fraction=0.5 so both 1/8 and full Kelly stay uncapped and distinguishable).
repeated_bets = pd.DataFrame([
    {"date": f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}", "market": "over25",
     "model_p": 0.55, "odds_close": 2.00}
    for i in range(60)
])
low_mult = simulate_bankroll(repeated_bets, kelly_mult=0.125, n_trials=3000,
                             start_bankroll=100.0, max_fraction=0.5, seed=7)
high_mult = simulate_bankroll(repeated_bets, kelly_mult=1.0, n_trials=3000,
                              start_bankroll=100.0, max_fraction=0.5, seed=7)
assert high_mult["final_bankroll"].std() > low_mult["final_bankroll"].std(), (
    "full Kelly should show higher bankroll variance than 1/8 Kelly on identical bets"
)
assert high_mult["ruined"].mean() > low_mult["ruined"].mean(), (
    "full Kelly should ruin more often than 1/8 Kelly on identical bets"
)

print("kelly_simulation_test: simulate_bankroll OK")
```

Append this block immediately after the existing
`print("kelly_simulation_test: filter_value_bets OK")` line from Task 1 — don't remove
that line, each section gets its own confirmation print, and they accumulate as more
sections are added in later tasks.

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/kelly_simulation_test.py`
Expected: `ImportError: cannot import name 'simulate_bankroll' from 'footymodel.simulate'`

- [ ] **Step 3: Write minimal implementation**

Append to `footymodel/simulate.py`:

```python


def simulate_bankroll(bets: pd.DataFrame, kelly_mult: float | None,
                       n_trials: int = 10_000, start_bankroll: float = 100.0,
                       max_fraction: float = 0.02, seed: int | None = None) -> dict:
    """Run n_trials independent simulated seasons over `bets`, in the given order.

    Each trial draws its own win/loss outcome per bet from a Bernoulli(model_p)
    distribution (parametric Monte Carlo - the real historical outcome is not
    used). kelly_mult=None means flat staking: 1 unit (1% of start_bankroll)
    per bet, fixed, non-compounding, matching backtest.py's flat convention.
    Otherwise stakes via staking.recommended_stake(), unmodified.

    "Ruined" = bankroll falls to or below RUIN_FLOOR_FRACTION * start_bankroll
    (proportional Kelly staking can only asymptotically approach zero, so a
    literal bankroll<=0 definition would never trigger for Kelly strategies -
    see the design spec for the full rationale). Once ruined, a trial stops
    processing further bets (bankroll frozen at the ruin value).

    Returns {"final_bankroll": np.ndarray, "max_drawdown": np.ndarray,
             "ruined": np.ndarray[bool]}, each of shape (n_trials,).
    """
    rng = np.random.default_rng(seed)
    probs = bets["model_p"].to_numpy()
    odds = bets["odds_close"].to_numpy()
    n_bets = len(probs)
    ruin_floor = start_bankroll * RUIN_FLOOR_FRACTION
    flat_stake = start_bankroll * 0.01

    final_bankroll = np.empty(n_trials)
    max_drawdown = np.empty(n_trials)
    ruined = np.zeros(n_trials, dtype=bool)

    for t in range(n_trials):
        bankroll = start_bankroll
        peak = start_bankroll
        worst_dd = 0.0
        outcomes = rng.random(n_bets) < probs

        for i in range(n_bets):
            if bankroll <= ruin_floor:
                ruined[t] = True
                break

            if kelly_mult is None:
                stake = min(flat_stake, bankroll)
            else:
                stake = recommended_stake(bankroll, probs[i], odds[i],
                                          kelly_mult=kelly_mult, max_fraction=max_fraction)
            if stake <= 0:
                continue

            if outcomes[i]:
                bankroll += stake * (odds[i] - 1.0)
            else:
                bankroll -= stake

            peak = max(peak, bankroll)
            if peak > 0:
                worst_dd = max(worst_dd, (peak - bankroll) / peak)

        final_bankroll[t] = max(bankroll, 0.0)
        max_drawdown[t] = worst_dd

    return {"final_bankroll": final_bankroll, "max_drawdown": max_drawdown, "ruined": ruined}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/kelly_simulation_test.py`
Expected:
```
kelly_simulation_test: filter_value_bets OK
kelly_simulation_test: simulate_bankroll OK
```

- [ ] **Step 5: Commit**

```bash
git add footymodel/simulate.py scripts/kelly_simulation_test.py
git commit -m "Add simulate_bankroll() Monte Carlo trial loop"
```

---

## Task 3: `footymodel/simulate.py` — `sweep()`

**Files:**
- Modify: `footymodel/simulate.py`
- Modify: `scripts/kelly_simulation_test.py`

- [ ] **Step 1: Write the failing test**

Append to `scripts/kelly_simulation_test.py`, before the module's final line:

```python
# --- sweep -----------------------------------------------------------
from footymodel.simulate import sweep, STRATEGIES

sweep_bets = pd.DataFrame([
    {"date": f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}", "market": "over25",
     "model_p": 0.55, "odds_close": 2.00}
    for i in range(60)
])
sweep_df = sweep(sweep_bets, n_trials=500, start_bankroll=100.0, seed=3)

assert len(sweep_df) == len(STRATEGIES)
assert list(sweep_df["strategy"]) == [label for label, _ in STRATEGIES]
assert (sweep_df["n_trials"] == 500).all()
assert (sweep_df["n_bets"] == 60).all()
for col in ["median_final_bankroll", "p5_final_bankroll", "p95_final_bankroll",
            "median_max_drawdown", "ruin_probability"]:
    assert col in sweep_df.columns
    assert sweep_df[col].notna().all()
# flat strategy's kelly_mult column should be empty (not a float), the rest numeric.
assert sweep_df.iloc[0]["strategy"] == "flat"
assert sweep_df.iloc[0]["kelly_mult"] == ""
assert sweep_df.iloc[1]["kelly_mult"] == 0.125

print("kelly_simulation_test: sweep OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/kelly_simulation_test.py`
Expected: `ImportError: cannot import name 'sweep' from 'footymodel.simulate'`

- [ ] **Step 3: Write minimal implementation**

Append to `footymodel/simulate.py`:

```python


def sweep(bets: pd.DataFrame, n_trials: int = 10_000, start_bankroll: float = 100.0,
          max_fraction: float = 0.02, seed: int | None = 0) -> pd.DataFrame:
    """Run every strategy in STRATEGIES over `bets`, return one summary row each.

    All strategies use the same rng seed, so each is evaluated against the
    identical sequence of simulated win/loss draws per trial - a paired
    comparison, not five independently-noisy runs.
    """
    rows = []
    for label, kelly_mult in STRATEGIES:
        result = simulate_bankroll(bets, kelly_mult, n_trials=n_trials,
                                   start_bankroll=start_bankroll,
                                   max_fraction=max_fraction, seed=seed)
        fb = result["final_bankroll"]
        rows.append({
            "strategy": label,
            "kelly_mult": kelly_mult if kelly_mult is not None else "",
            "n_trials": n_trials,
            "n_bets": len(bets),
            "median_final_bankroll": float(np.median(fb)),
            "p5_final_bankroll": float(np.percentile(fb, 5)),
            "p95_final_bankroll": float(np.percentile(fb, 95)),
            "median_max_drawdown": float(np.median(result["max_drawdown"])),
            "ruin_probability": float(result["ruined"].mean()),
        })
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python scripts/kelly_simulation_test.py`
Expected:
```
kelly_simulation_test: filter_value_bets OK
kelly_simulation_test: simulate_bankroll OK
kelly_simulation_test: sweep OK
```

- [ ] **Step 5: Commit**

```bash
git add footymodel/simulate.py scripts/kelly_simulation_test.py
git commit -m "Add sweep() to compare Kelly fractions side by side"
```

---

## Task 4: `scripts/kelly_simulation.py` — CLI

**Files:**
- Create: `scripts/kelly_simulation.py`

- [ ] **Step 1: Write the script**

```python
"""Kelly-fraction bankroll Monte Carlo simulator - CLI.

Runs footymodel.simulate.sweep() over the E0 O/U 2.5 backtested value bets
and writes data/processed/kelly_simulation.csv for the dashboard's Staking
tab. Manual/periodic - only depends on evals_main.parquet (built by
scripts/ou_strategy.py or scripts/best_price.py), which only changes when
the backtest is re-run, so this isn't wired into the live poller.

Usage:
    python scripts/kelly_simulation.py
    python scripts/kelly_simulation.py --n-trials 20000 --start-bankroll 200
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.simulate import SIM_OUTPUT_PATH, load_value_bets, sweep


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-trials", type=int, default=10_000)
    parser.add_argument("--start-bankroll", type=float, default=100.0)
    parser.add_argument("--edge-threshold", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    bets = load_value_bets(edge_threshold=args.edge_threshold)
    print(f"Loaded {len(bets)} E0 O/U 2.5 value bets "
          f"({bets['date'].min()} to {bets['date'].max()})")

    result = sweep(bets, n_trials=args.n_trials, start_bankroll=args.start_bankroll,
                   seed=args.seed)
    result.to_csv(SIM_OUTPUT_PATH, index=False)
    print(f"Saved -> {SIM_OUTPUT_PATH}\n")

    print(f"{'strategy':>13} {'median':>9} {'p5':>9} {'p95':>9} {'maxDD':>7} {'ruin%':>7}")
    for _, r in result.iterrows():
        print(f"{r['strategy']:>13} {r['median_final_bankroll']:>9.1f} "
              f"{r['p5_final_bankroll']:>9.1f} {r['p95_final_bankroll']:>9.1f} "
              f"{r['median_max_drawdown']*100:>6.1f}% {r['ruin_probability']*100:>6.1f}%")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it runs**

Run: `python scripts/kelly_simulation.py`
Expected: prints `Loaded 547 E0 O/U 2.5 value bets (...)`, then `Saved -> .../kelly_simulation.csv`,
then a 5-row summary table (flat, kelly-0.125, kelly-0.25, kelly-0.5, kelly-1.0). Requires
`data/processed/evals_main.parquet` to already exist locally (built earlier this session);
if missing, run `python scripts/ou_strategy.py` first to build it.

- [ ] **Step 3: Commit**

```bash
git add scripts/kelly_simulation.py
git commit -m "Add CLI script for the Kelly bankroll simulator"
```

---

## Task 5: Wire the test into CI

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add the new test step**

In `.github/workflows/ci.yml`, after the existing "Grade-results mixed-format kickoff
parsing" step, add:

```yaml
      - name: Kelly bankroll simulator (pure, data-free)
        run: python scripts/kelly_simulation_test.py
```

- [ ] **Step 2: Verify locally**

Run: `python -m compileall -q footymodel scripts && python scripts/kelly_simulation_test.py`
Expected: no compile errors, then the same 3-line OK output as Task 3.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "Run the Kelly simulator test in CI"
```

---

## Task 6: Generate and track the real simulation output

**Files:**
- Modify: `.gitignore`
- Create (generated, then tracked): `data/processed/kelly_simulation.csv`

- [ ] **Step 1: Un-ignore the output CSV**

In `.gitignore`, add a new line after `!data/processed/graded_results.csv`:

```
!data/processed/kelly_simulation.csv
```

- [ ] **Step 2: Generate the real CSV**

Run: `python scripts/kelly_simulation.py`
Expected: same output as Task 4 Step 2, and `data/processed/kelly_simulation.csv` now
exists on disk with 5 rows.

- [ ] **Step 3: Verify git will track it**

Run: `git status --short data/processed/kelly_simulation.csv`
Expected: `?? data/processed/kelly_simulation.csv` (untracked, not ignored — if the
`.gitignore` exception hadn't taken effect, this command would print nothing at all).

- [ ] **Step 4: Commit**

```bash
git add .gitignore data/processed/kelly_simulation.csv
git commit -m "Track the generated Kelly simulation output CSV"
```

---

## Task 7: `dashboard/lib/data.ts` — `getKellySimResults()`

**Files:**
- Modify: `dashboard/lib/data.ts`

- [ ] **Step 1: Add the type and fetch function**

In `dashboard/lib/data.ts`, after the `GradedResult` type block (before the `PropsPick`
type), add:

```ts
export type KellySimResult = {
  strategy: string;
  kellyMult: number | null;
  nTrials: number;
  nBets: number;
  medianFinalBankroll: number;
  p5FinalBankroll: number;
  p95FinalBankroll: number;
  medianMaxDrawdown: number;
  ruinProbability: number;
};
```

After the existing `getGradedResults()` function (end of file), add:

```ts

export async function getKellySimResults(): Promise<KellySimResult[]> {
  const rows = await fetchCsv("kelly_simulation.csv");
  return rows
    .map((r) => ({
      strategy: r.strategy,
      kellyMult: num(r.kelly_mult),
      nTrials: num(r.n_trials) ?? 0,
      nBets: num(r.n_bets) ?? 0,
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

- [ ] **Step 2: Type-check**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd dashboard && git add lib/data.ts && git commit -m "Add getKellySimResults() to the dashboard data layer"
```

---

## Task 8: `dashboard/components/StakingPanel.tsx`

**Files:**
- Create: `dashboard/components/StakingPanel.tsx`

- [ ] **Step 1: Write the component**

```tsx
import type { KellySimResult } from "@/lib/data";

const STRATEGY_LABELS: Record<string, string> = {
  flat: "Flat stake",
  "kelly-0.125": "1/8 Kelly",
  "kelly-0.25": "1/4 Kelly",
  "kelly-0.5": "1/2 Kelly",
  "kelly-1.0": "Full Kelly",
};

function multiple(finalBankroll: number, startBankroll: number) {
  return `${(finalBankroll / startBankroll).toFixed(2)}x`;
}

export default function StakingPanel({ results }: { results: KellySimResult[] }) {
  if (results.length === 0) {
    return (
      <section>
        <h2 className="text-lg font-semibold mb-1">Staking — Kelly bankroll simulation</h2>
        <p className="text-sm text-neutral-500">
          No simulation results yet — run{" "}
          <code className="font-mono text-xs">python scripts/kelly_simulation.py</code>.
        </p>
      </section>
    );
  }

  const startBankroll = 100;

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Staking — Kelly bankroll simulation</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Monte Carlo over the {results[0].nBets} backtested E0 O/U 2.5 value bets,{" "}
        {results[0].nTrials.toLocaleString()} simulated seasons per strategy. Downstream
        risk-sizing analysis only — doesn&apos;t affect the model&apos;s predictions or
        edge. &quot;Ruin&quot; means bankroll fell to 5% of its starting value.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {results.map((r, i) => (
          <div
            key={r.strategy}
            className="animate-stagger-in rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 transition-transform duration-150 hover:-translate-y-0.5"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <div className="text-sm font-medium">
              {STRATEGY_LABELS[r.strategy] ?? r.strategy}
            </div>
            <div className="text-xl font-mono mt-1">
              {multiple(r.medianFinalBankroll, startBankroll)}
            </div>
            <div className="text-xs text-neutral-400 mt-0.5">median final bankroll</div>
            <div className="mt-3 flex justify-between text-xs">
              <span className="text-neutral-500">Max drawdown</span>
              <span className="font-mono">{(r.medianMaxDrawdown * 100).toFixed(0)}%</span>
            </div>
            <div className="mt-1 flex justify-between text-xs">
              <span className="text-neutral-500">Risk of ruin</span>
              <span
                className={`font-mono ${
                  r.ruinProbability > 0.05
                    ? "text-red-500 dark:text-red-400"
                    : "text-emerald-600 dark:text-emerald-400"
                }`}
              >
                {(r.ruinProbability * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Type-check**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no errors (this component isn't wired into a page yet, but it must still
type-check standalone).

- [ ] **Step 3: Commit**

```bash
cd dashboard && git add components/StakingPanel.tsx && git commit -m "Add StakingPanel component"
```

---

## Task 9: Wire the "Staking" tab into `DashboardTabs` and `page.tsx`

**Files:**
- Modify: `dashboard/components/DashboardTabs.tsx`
- Modify: `dashboard/app/page.tsx`

- [ ] **Step 1: Add the 4th tab to `DashboardTabs.tsx`**

In `dashboard/components/DashboardTabs.tsx`:

Change:
```ts
const TABS = ["Track record", "Goals O/U", "Player props"];
```
to:
```ts
const TABS = ["Track record", "Goals O/U", "Player props", "Staking"];
```

Change the props type and destructuring from:
```tsx
export default function DashboardTabs({
  trackRecord,
  goals,
  props,
}: {
  trackRecord: ReactNode;
  goals: ReactNode;
  props: ReactNode;
}) {
  const [active, setActive] = useState(0);
  const panels = [trackRecord, goals, props];
```
to:
```tsx
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

(The clip-path pill-width math already derives from `TABS.length`, so no other change is
needed there.)

- [ ] **Step 2: Wire it up in `page.tsx`**

In `dashboard/app/page.tsx`, change the import line:
```ts
import {
  getGoalsPicks,
  getPropsPicks,
  getGradedResults,
  getMostProbablePicks,
  type GoalsPick,
  type GradedResult,
} from "@/lib/data";
```
to:
```ts
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

Add the import for the new panel, after `import PropsPanel from "@/components/PropsPanel";`:
```ts
import StakingPanel from "@/components/StakingPanel";
```

Change the data fetch:
```ts
  const [goals, props, graded] = await Promise.all([
    getGoalsPicks(),
    getPropsPicks(),
    getGradedResults(),
  ]);
  const mostProbable = getMostProbablePicks(props);
```
to:
```ts
  const [goals, props, graded, kellySim] = await Promise.all([
    getGoalsPicks(),
    getPropsPicks(),
    getGradedResults(),
    getKellySimResults(),
  ]);
  const mostProbable = getMostProbablePicks(props);
```

Change the `<DashboardTabs>` call:
```tsx
      <DashboardTabs
        trackRecord={<TrackRecordPanel graded={graded} />}
        goals={<GoalsPanel goals={goals} />}
        props={<PropsPanel props={props} mostProbable={mostProbable} />}
      />
```
to:
```tsx
      <DashboardTabs
        trackRecord={<TrackRecordPanel graded={graded} />}
        goals={<GoalsPanel goals={goals} />}
        props={<PropsPanel props={props} mostProbable={mostProbable} />}
        staking={<StakingPanel results={kellySim} />}
      />
```

- [ ] **Step 3: Build**

Run (from `dashboard/`): `npx tsc --noEmit && npm run build`
Expected: both clean, no errors.

- [ ] **Step 4: Commit**

```bash
cd dashboard && git add components/DashboardTabs.tsx app/page.tsx
git commit -m "Add Staking tab to the dashboard"
```

---

## Task 10: Verify in the browser and deploy

**Files:** none (verification + deploy only)

- [ ] **Step 1: Start the dashboard locally and open it**

Use the project's preview tooling to start the dev server and open the dashboard in a
browser tab.

- [ ] **Step 2: Click through the Staking tab**

Click the "Staking" tab (4th pill). Confirm: the pill slides to the 4th position, 5 stat
cards render (Flat stake, 1/8 Kelly, 1/4 Kelly, 1/2 Kelly, Full Kelly) with staggered
entrance, each showing a median-bankroll multiple, max drawdown %, and risk-of-ruin %.
Confirm ruin probability generally increases and drawdown widens as the Kelly fraction
increases (full Kelly should show visibly higher risk than 1/8 Kelly).

- [ ] **Step 3: Check the other three tabs still work**

Click through Track Record, Goals O/U, and Player Props — confirm no regressions from
the `DashboardTabs` prop-type change.

- [ ] **Step 4: Deploy to Vercel production**

Run (from `dashboard/`): `vercel deploy --prod --yes`
Expected: deployment succeeds, aliased to the existing production URL.

- [ ] **Step 5: Verify production**

Navigate to the production URL, click the Staking tab, confirm real data renders (not
"No simulation results yet").

---

## Plan self-review notes

- **Spec coverage:** `filter_value_bets`/`load_value_bets` (Task 1) ✓, `simulate_bankroll`
  with the corrected 5%-floor ruin definition (Task 2) ✓, `sweep` (Task 3) ✓, CLI script
  (Task 4) ✓, CI wiring (Task 5) ✓, tracked CSV output (Task 6) ✓, dashboard data layer
  (Task 7) ✓, `StakingPanel` (Task 8) ✓, 4th tab wiring (Task 9) ✓, browser + prod
  verification (Task 10) ✓. All spec sections have a corresponding task.
- **Placeholder scan:** no TBD/TODO; every step has complete, runnable code.
- **Type consistency:** `KellySimResult` fields match between Task 7's `data.ts` and
  Task 8's `StakingPanel.tsx` (`kellyMult`, `nTrials`, `nBets`,
  `medianFinalBankroll`/`p5FinalBankroll`/`p95FinalBankroll`, `medianMaxDrawdown`,
  `ruinProbability`) — checked field-by-field. `STRATEGIES` labels in `simulate.py`
  (`flat`, `kelly-0.125`, `kelly-0.25`, `kelly-0.5`, `kelly-1.0`) match
  `STRATEGY_LABELS` keys in `StakingPanel.tsx`.
