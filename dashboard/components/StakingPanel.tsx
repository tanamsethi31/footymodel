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

  const startBankroll = results[0].startBankroll;

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
