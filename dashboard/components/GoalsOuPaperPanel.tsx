import type { GoalsPick, PaperBet } from "@/lib/data";
import { pct } from "@/lib/format";

export default function GoalsOuPaperPanel({
  goals,
  paperBets,
}: {
  goals: GoalsPick[];
  paperBets: PaperBet[];
}) {
  const goalsBets = paperBets.filter((b) => b.betKind === "goals_ou");
  const recent = goals.slice(0, 12);

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Goals Over/Under 2.5</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Lineup-aware model (25% team / 75% confirmed XI blend). Live via SofaScore on
        home Wi‑Fi; paper stakes only when book O/U odds and EV ≥ 2% are available.
      </p>

      {goalsBets.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium mb-2">Open paper O/U bets</h3>
          <ul className="text-sm space-y-2">
            {goalsBets
              .filter((b) => b.status === "open")
              .map((b) => (
                <li key={b.betId} className="font-mono text-xs sm:text-sm">
                  {b.home} v {b.away} · {b.market.replace("ou_", "").replace("25", " 2.5")} ·
                  €{b.stakeEur.toFixed(2)} @ {b.decimalOdds?.toFixed(2)} · p=
                  {pct(b.modelP)}
                </li>
              ))}
          </ul>
        </div>
      )}

      <h3 className="text-sm font-medium mb-2">Recent model lines</h3>
      {recent.length === 0 ? (
        <p className="text-sm text-neutral-500">No live goals recommendations logged yet.</p>
      ) : (
        <ul className="text-sm space-y-3">
          {recent.map((g) => (
            <li
              key={`${g.fixtureId}-${g.loggedAt}`}
              className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3"
            >
              <div className="font-medium">{g.home} v {g.away}</div>
              <div className="text-xs text-neutral-500 mt-1">
                P(O2.5) {pct(g.modelPOver25)} · xG {g.expTotalGoals.toFixed(2)}
                {g.evOver25 != null && g.oddsOver25 != null && (
                  <>
                    {" "}
                    · O {g.oddsOver25.toFixed(2)} EV {(g.evOver25 * 100).toFixed(1)}%
                  </>
                )}
                {g.evUnder25 != null && g.oddsUnder25 != null && (
                  <>
                    {" "}
                    · U {g.oddsUnder25.toFixed(2)} EV {(g.evUnder25 * 100).toFixed(1)}%
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
