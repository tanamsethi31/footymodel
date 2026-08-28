# Kelly bankroll Monte Carlo simulator — design

Status: approved (R037–R043 in `.ladder/ladder.md`)

## Purpose

A downstream staking/risk-sizing analysis, not a predictive-model improvement. It takes
the existing backtested edge (E0 goals O/U 2.5, t=2.23) as given and answers: at what
Kelly fraction is the staking approach safe, in terms of risk of ruin, drawdown, and
bankroll growth? Useful if real staking is ever considered, and as a standalone
quant/portfolio artifact regardless (VISION.md §9).

Explicitly out of scope: finding new edge, improving model accuracy/calibration,
new markets or leagues. Those are separate tracks (R007, R010).

## Data source

`data/processed/evals_main.parquet` — the existing walk-forward backtest evaluation
output (36,525 rows: date, league, market, home, away, model_p, won, odds_open,
odds_close, fair_open, fair_close). Filtered to:

- `league == "E0"`, `market in ("over25", "under25")`
- `edge = model_p * odds_close - 1 > 0.05` (same value-bet threshold `backtest.py` uses)

This yields 547 real positive-EV bets spanning 2022-08-06 to 2025-05-25 (136 over25,
411 under25). Bets are kept in chronological order — the simulation always applies them
in the order they actually happened; only the win/loss draw is randomized per trial.

## Simulation engine — `footymodel/simulate.py`

```python
def load_value_bets(league="E0", markets=("over25", "under25"), edge_threshold=0.05) -> pd.DataFrame
```
Reads `evals_main.parquet`, filters and sorts as above. Returns columns:
`date, market, model_p, odds_close`.

```python
def simulate_bankroll(bets: pd.DataFrame, strategy: str, kelly_mult: float | None,
                       n_trials: int = 10_000, start_bankroll: float = 100.0,
                       max_fraction: float = 0.02) -> dict
```
Runs `n_trials` independent simulated seasons over the same 547-bet sequence. For each
trial:

1. Start at `start_bankroll`.
2. For each bet in order: draw `won = random() < model_p` (parametric Bernoulli — the
   real historical outcome is *not* used here, only the model's own probability. This
   is deliberate: it explores variance the 3-season sample never happened to produce,
   and it means the simulation is only as trustworthy as the model's calibration).
3. Size the stake:
   - `strategy == "flat"`: a fixed stake of 1 unit of the *starting* bankroll on every
     bet (non-compounding — matches `backtest.py`'s existing flat-staking convention
     exactly), regardless of edge size or how the bankroll has moved since. This is
     the baseline.
   - `strategy == "kelly"`: `staking.recommended_stake(bankroll, model_p, odds_close,
     kelly_mult, max_fraction)` — reuses the existing module as-is, no changes to it.
4. Update bankroll: win → `+= stake * (odds_close - 1)`; loss → `-= stake`.
5. Track running peak bankroll; drawdown at each step = `(peak - bankroll) / peak`.
6. If `bankroll <= 0`: mark the trial ruined, stop processing further bets in that
   trial (bankroll frozen at the ruin value).

Returns per-trial arrays (`final_bankroll`, `max_drawdown`, `ruined: bool`) which the
caller reduces to summary statistics.

```python
def sweep(bets: pd.DataFrame, n_trials=10_000, start_bankroll=100.0) -> pd.DataFrame
```
Runs five strategies — `flat`, `kelly-0.125`, `kelly-0.25` (staking.py's current
default), `kelly-0.5`, `kelly-1.0` (full Kelly) — and returns one summary row per
strategy:

| column | meaning |
|---|---|
| `strategy` | label, e.g. `kelly-0.25` |
| `kelly_mult` | numeric multiplier, or empty for flat |
| `n_trials`, `n_bets` | 10000, 547 |
| `median_final_bankroll`, `p5_final_bankroll`, `p95_final_bankroll` | percentiles of ending bankroll across trials, starting from 100 |
| `median_max_drawdown` | median of each trial's max drawdown |
| `ruin_probability` | fraction of trials where `ruined == True` |

Writes this to `data/processed/kelly_simulation.csv`.

## Script — `scripts/kelly_simulation.py`

Thin CLI wrapper matching the existing `scripts/ah_backtest.py` pattern: parses
`--n-trials`, `--start-bankroll`, `--edge-threshold` (all optional, sane defaults),
calls `simulate.load_value_bets()` + `simulate.sweep()`, writes the CSV, prints the
summary table to stdout.

Run manually / periodically (not wired into `live_poll.yml` or `grade_results.yml` —
this only depends on the backtest evals, which don't change without a manual
`backtest.py` re-run, so there's nothing for a cron job to pick up).

## Testing — `scripts/kelly_simulation_test.py`

Matches the existing `scripts/*_test.py` convention (assert-based `demo()`/`__main__`,
no framework). Checks, on a small synthetic bet set with known edge:

- Higher `kelly_mult` produces higher variance: wider spread of `final_bankroll`
  across trials, and higher `ruin_probability`, than a lower `kelly_mult` on the same
  bet set.
- `flat` strategy never ruins when every synthetic bet is a guaranteed win
  (`model_p = 1.0`).
- `simulate_bankroll` with `kelly_mult=0.25` on one bet matches
  `staking.recommended_stake()` called directly with the same inputs (integration
  check — confirms the simulator is actually using the real staking module, not a
  reimplementation).

## Dashboard integration

`dashboard/lib/data.ts`:
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

export async function getKellySimResults(): Promise<KellySimResult[]>
```
Fetches `kelly_simulation.csv` via the same `fetchCsv()` / GitHub Contents API pattern
already used for the other three CSVs. Returns `[]` on 404 (file not yet generated),
consistent with the existing empty-state handling.

New 4th tab, **"Staking"**, added to `DashboardTabs` (`TABS` array grows to 4 — the
clip-path math already derives from `TABS.length`, so no changes needed there beyond
adding the label and a fourth panel prop).

New `components/StakingPanel.tsx` (server component, no interactivity needed — this is
static computed data, unlike the props threshold toggle): one stat card per strategy,
same `rounded-xl border ... p-4` visual language as the existing Track Record cards,
same `animate-stagger-in` entrance. Each card shows: strategy label, median final
bankroll (as a multiple of starting bankroll, e.g. "2.4x"), max drawdown, ruin
probability. Sorted by `kelly_mult` ascending (flat first, full Kelly last).

If `kelly_simulation.csv` doesn't exist yet, the panel shows the same "no data yet"
text pattern used elsewhere (e.g. `PropsPanel`'s "No prop predictions logged yet.").

## Out of scope for v1

- No live-poller / CI wiring (manual script run only).
- No new npm chart dependency — summary stat cards only, no trajectory fan chart.
- No changes to `footymodel/staking.py` itself — the simulator calls it as-is.
- No bootstrap-resampling mode (parametric Bernoulli only).
