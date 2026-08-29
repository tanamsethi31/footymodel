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
import { formatKickoff, pct, odds, EvBadge } from "@/lib/format";
import Logo from "@/components/Logo";
import SubscribeButton from "@/components/SubscribeButton";
import DashboardTabs from "@/components/DashboardTabs";
import MatchCard from "@/components/MatchCard";
import PropsPanel from "@/components/PropsPanel";
import StakingPanel from "@/components/StakingPanel";
import GlossaryPanel from "@/components/GlossaryPanel";

export const revalidate = 60;

function TrackRecordPanel({ graded }: { graded: GradedResult[] }) {
  const gradedBets = graded.filter((g) => g.betSide !== null);
  const accuracy =
    graded.length > 0
      ? graded.filter((g) => g.modelCorrect).length / graded.length
      : null;
  const betWinRate =
    gradedBets.length > 0
      ? gradedBets.filter((g) => g.betWon).length / gradedBets.length
      : null;
  const cumulativeReturn = gradedBets.reduce(
    (sum, g) => sum + (g.realizedReturn ?? 0),
    0
  );

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Track record</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Goals predictions only (v1): graded against real results once a match
        finishes. &quot;Bet&quot; means the model showed positive EV on a side
        at the time it was logged; still paper-trade, no real money moved.
      </p>
      {graded.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No graded results yet. Predictions get graded the day after
          they&apos;re logged, once the match has finished.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
              <div className="text-neutral-500 text-xs">Model accuracy</div>
              <div className="text-xl font-mono mt-1">{pct(accuracy)}</div>
              <div className="text-xs text-neutral-400 mt-0.5">
                {graded.length} graded
              </div>
            </div>
            <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
              <div className="text-neutral-500 text-xs">Bets placed</div>
              <div className="text-xl font-mono mt-1">{gradedBets.length}</div>
              <div className="text-xs text-neutral-400 mt-0.5">
                positive EV at the time
              </div>
            </div>
            <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
              <div className="text-neutral-500 text-xs">Bet win rate</div>
              <div className="text-xl font-mono mt-1">{pct(betWinRate)}</div>
            </div>
            <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
              <div className="text-neutral-500 text-xs">Cumulative return</div>
              <div className="mt-1">
                <EvBadge ev={gradedBets.length > 0 ? cumulativeReturn : null} />
              </div>
              <div className="text-xs text-neutral-400 mt-0.5">in stake units</div>
            </div>
          </div>

          <div className="space-y-2">
            {graded.map((g, i) => (
              <div
                key={g.fixtureId}
                className="animate-stagger-in rounded-lg border border-neutral-200 dark:border-neutral-800 px-4 py-2.5 flex items-center justify-between gap-3 flex-wrap text-sm transition-transform duration-150 hover:-translate-y-0.5"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <div>
                  <span className="font-medium">
                    {g.home} {g.actualHomeGoals}-{g.actualAwayGoals} {g.away}
                  </span>
                  <span className="text-neutral-400 ml-2">{formatKickoff(g.kickoff)}</span>
                </div>
                <div className="flex items-center gap-3 font-mono text-xs">
                  <span
                    className={
                      g.modelCorrect
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-red-500 dark:text-red-400"
                    }
                  >
                    model {g.modelCorrect ? "✓" : "✗"}
                  </span>
                  {g.betSide && (
                    <span
                      className={
                        g.betWon
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-red-500 dark:text-red-400"
                      }
                    >
                      bet {g.betSide} @ {odds(g.betOdds)}{" "}
                      {g.realizedReturn !== null &&
                        `(${g.realizedReturn > 0 ? "+" : ""}${g.realizedReturn.toFixed(2)})`}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function GoalsPanel({
  goals,
  matchDetails,
}: {
  goals: GoalsPick[];
  matchDetails: Record<string, MatchDetail>;
}) {
  // "Upcoming" only - a match that's already kicked off isn't a live pick
  // anymore. Finished matches move to the Track Record tab once graded;
  // this tab is specifically about what's coming up next.
  const upcoming = goals.filter((g) => new Date(g.kickoff).getTime() > Date.now());
  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Goals: Over/Under 2.5</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Confirmed-lineup model, pooled t=3.04 backtested (individually
        significant on the Premier League alone, t=2.23).
      </p>
      {upcoming.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No upcoming predictions right now. Check back once a fixture&apos;s
          lineup is confirmed pre-kickoff.
        </p>
      ) : (
        <div className="space-y-3">
          {upcoming.map((g, i) => (
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

export default async function Home() {
  const [goals, props, graded, kellySim, matchDetails] = await Promise.all([
    getGoalsPicks(),
    getPropsPicks(),
    getGradedResults(),
    getKellySimResults(),
    getMatchDetails(),
  ]);
  const mostProbable = getMostProbablePicks(props);

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 sm:py-14 w-full">
      <header className="flex items-start justify-between gap-4 mb-10">
        <div>
          <Logo />
          <p className="text-sm text-neutral-500 mt-1">
            Live predictions for Premier League goals O/U 2.5 and player shots /
            shots-on-target, both backtested. Paper-trade only, nothing here
            is a real bet.
          </p>
        </div>
        <SubscribeButton />
      </header>

      <DashboardTabs
        trackRecord={<TrackRecordPanel graded={graded} />}
        goals={<GoalsPanel goals={goals} matchDetails={matchDetails} />}
        props={<PropsPanel props={props} mostProbable={mostProbable} />}
        staking={<StakingPanel results={kellySim} />}
        glossary={<GlossaryPanel />}
      />

      <footer className="mt-16 text-xs text-neutral-400">
        Research project. Paper-trade only, no real money involved. Refreshes
        automatically as new predictions are logged.
      </footer>
    </div>
  );
}
