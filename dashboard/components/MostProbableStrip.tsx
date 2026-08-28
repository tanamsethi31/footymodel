import type { MostProbablePick } from "@/lib/data";
import { odds as fmtOdds } from "@/lib/format";

export default function MostProbableStrip({ picks }: { picks: MostProbablePick[] }) {
  if (picks.length === 0) return null;

  return (
    <div className="mb-8">
      <p className="text-xs uppercase tracking-wide text-neutral-400 dark:text-neutral-500 mb-3">
        Most probable bets
      </p>
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
        {picks.map((p, i) => (
          <div
            key={`${p.fixtureId}-${p.player}-${p.marketLabel}`}
            className="animate-stagger-in shrink-0 w-44 rounded-xl border border-neutral-200 dark:border-neutral-800 p-3.5 transition-transform duration-150 hover:-translate-y-0.5"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            <div className="text-sm font-semibold truncate">{p.player}</div>
            <div className="text-[11px] text-neutral-400 mb-2 truncate">{p.team}</div>
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-neutral-500">{p.marketLabel}</span>
              <span className="font-mono text-base font-semibold text-emerald-600 dark:text-emerald-400">
                {(p.prob * 100).toFixed(0)}%
              </span>
            </div>
            {p.odds !== null && (
              <div className="text-[11px] text-neutral-400 font-mono mt-0.5">
                @ {fmtOdds(p.odds)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
