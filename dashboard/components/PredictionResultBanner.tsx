import type { GradedResult } from "@/lib/data";
import { odds } from "@/lib/format";

export default function PredictionResultBanner({ graded }: { graded: GradedResult }) {
  const totalGoals = graded.actualTotalGoals;
  const ouLabel = graded.actualOverWon ? "Over 2.5" : "Under 2.5";

  return (
    <div className="mt-3 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/50 px-3 py-2.5">
      <div className="flex items-center justify-between gap-2 flex-wrap text-sm">
        <span className="font-medium">
          {graded.home} {graded.actualHomeGoals}-{graded.actualAwayGoals} {graded.away}
        </span>
        <span className="text-xs text-neutral-500">
          {totalGoals} goals · {ouLabel}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-3 flex-wrap text-xs font-mono">
        <span
          className={
            graded.modelCorrect
              ? "text-emerald-600 dark:text-emerald-400"
              : "text-red-500 dark:text-red-400"
          }
        >
          Model {graded.modelCorrect ? "correct" : "wrong"}
        </span>
        {graded.betSide ? (
          <span
            className={
              graded.betWon
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-500 dark:text-red-400"
            }
          >
            Bet {graded.betSide} @ {odds(graded.betOdds)}{" "}
            {graded.betWon ? "won" : "lost"}
            {graded.realizedReturn !== null && (
              <span className="ml-1">
                ({graded.realizedReturn > 0 ? "+" : ""}
                {graded.realizedReturn.toFixed(2)} units)
              </span>
            )}
          </span>
        ) : (
          <span className="text-neutral-400">No +EV bet logged</span>
        )}
      </div>
    </div>
  );
}
