import {
  getGoalsPicks,
  getPropsPicks,
  getGradedResults,
  getMostProbablePicks,
  getKellySimResults,
  getMatchDetails,
  getUpcomingFixtures,
  getWatchlists,
  type GoalsPick,
  type GradedResult,
  type MatchDetail,
  type UpcomingFixture,
} from "@/lib/data";
import { selectNextUpcoming, UPCOMING_DISPLAY_LIMIT } from "@/lib/upcoming";
import { formatKickoff, pct, odds, EvBadge } from "@/lib/format";
import Logo from "@/components/Logo";
import SubscribeButton from "@/components/SubscribeButton";
import RefreshButton from "@/components/RefreshButton";
import ThemeToggle from "@/components/ThemeToggle";
import DashboardTabs from "@/components/DashboardTabs";
import MatchCard from "@/components/MatchCard";
import PreviewMatchCard from "@/components/PreviewMatchCard";
import PastDisclosure from "@/components/PastDisclosure";
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
  nextFixtures,
}: {
  goals: GoalsPick[];
  matchDetails: Record<string, MatchDetail>;
  nextFixtures: UpcomingFixture[];
}) {
  // A match that's already kicked off isn't a live pick anymore - it moves
  // into the collapsed "past predictions" disclosure below instead of
  // cluttering the upcoming list (still checkable, just out of the way).
  const now = Date.now();
  const past = goals.filter((g) => new Date(g.kickoff).getTime() <= now);
  const predictedById = new Map(
    goals
      .filter((g) => new Date(g.kickoff).getTime() > now)
      .map((g) => [g.fixtureId, g])
  );
  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Goals: Over/Under 2.5</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Next {UPCOMING_DISPLAY_LIMIT} Premier League fixtures, kickoff order.
        Confirmed-lineup model (pooled t=3.04; PL alone t=2.23) fills in once
        XIs are announced.
      </p>
      {nextFixtures.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No upcoming Premier League fixtures in the current window.
        </p>
      ) : (
        <div className="space-y-3">
          {nextFixtures.map((f, i) => {
            const match = predictedById.get(f.fixtureId);
            if (match) {
              return (
                <MatchCard
                  key={f.fixtureId}
                  match={match}
                  detail={matchDetails[match.fixtureId] ?? null}
                  index={i}
                />
              );
            }
            return <PreviewMatchCard key={f.fixtureId} fixture={f} index={i} />;
          })}
        </div>
      )}
      <PastDisclosure count={past.length}>
        {past.map((g, i) => (
          <MatchCard
            key={g.fixtureId}
            match={g}
            detail={matchDetails[g.fixtureId] ?? null}
            index={i}
          />
        ))}
      </PastDisclosure>
    </section>
  );
}

export default async function Home() {
  const [goals, props, graded, kellySim, matchDetails, upcomingFixtures, watchlists] = await Promise.all([
    getGoalsPicks(),
    getPropsPicks(),
    getGradedResults(),
    getKellySimResults(),
    getMatchDetails(),
    getUpcomingFixtures(),
    getWatchlists(),
  ]);
  const nextFixtures = selectNextUpcoming(upcomingFixtures, goals);
  const nextIds = new Set(nextFixtures.map((f) => f.fixtureId));
  const upcomingProps = props.filter(
    (p) => nextIds.has(p.fixtureId) && new Date(p.kickoff).getTime() > Date.now()
  );
  const mostProbable = getMostProbablePicks(upcomingProps);

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 sm:py-14 w-full">
      <header className="flex flex-row items-start justify-between gap-4 mb-10">
        <div className="min-w-0 flex-1">
          <Logo />
          <p className="text-sm text-neutral-500 mt-1">
            Live predictions for Premier League goals O/U 2.5 and player shots /
            shots-on-target, both backtested. Paper-trade only, nothing here
            is a real bet.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          <div className="flex items-center gap-2">
            <RefreshButton />
            <SubscribeButton />
          </div>
          <ThemeToggle />
        </div>
      </header>

      <DashboardTabs
        trackRecord={<TrackRecordPanel graded={graded} />}
        goals={
          <GoalsPanel
            goals={goals}
            matchDetails={matchDetails}
            nextFixtures={nextFixtures}
          />
        }
        props={
          <PropsPanel
            props={props}
            mostProbable={mostProbable}
            nextFixtures={nextFixtures}
            watchlists={watchlists}
          />
        }
        staking={<StakingPanel results={kellySim} />}
        glossary={<GlossaryPanel />}
      />

      <footer className="mt-16 text-xs text-neutral-400">
        Research project. Paper-trade only, no real money involved. Data
        auto-updates about every minute; tap ↻ to refresh now (once per
        minute).
      </footer>
    </div>
  );
}
