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
  type FixtureWatchlist,
} from "@/lib/data";
import { buildFixtureTimeline, findLoggedFixture, isFixtureFinished, isFixtureLive } from "@/lib/fixtureTimeline";
import { buildGradedKeys, findGradedResult, sortPastPredictions } from "@/lib/graded";
import { PREMIER_LEAGUE } from "@/lib/league";
import { UPCOMING_DISPLAY_LIMIT, watchlistForFixture } from "@/lib/upcoming";
import { formatKickoff, pct, odds, EvBadge } from "@/lib/format";
import Logo from "@/components/Logo";
import SubscribeButton from "@/components/SubscribeButton";
import RefreshButton from "@/components/RefreshButton";
import ThemeToggle from "@/components/ThemeToggle";
import DashboardTabs from "@/components/DashboardTabs";
import MatchCard from "@/components/MatchCard";
import PreviewMatchCard from "@/components/PreviewMatchCard";
import FixtureTimelineSection from "@/components/FixtureTimelineSection";
import PastDisclosure from "@/components/PastDisclosure";
import PropsPanel, { isActivePropsFixture } from "@/components/PropsPanel";
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
  timeline,
  watchlists,
  graded,
}: {
  goals: GoalsPick[];
  matchDetails: Record<string, MatchDetail>;
  timeline: ReturnType<typeof buildFixtureTimeline>;
  watchlists: FixtureWatchlist[];
  graded: GradedResult[];
}) {
  const gradedKeys = buildGradedKeys(graded);
  const past = sortPastPredictions(
    goals.filter(
      (g) =>
        g.league === PREMIER_LEAGUE &&
        isFixtureFinished(g.kickoff, Date.now(), gradedKeys, g)
    )
  );

  function renderFixture(
    fixture: (typeof timeline.today)[number],
    index: number,
    emphasis: "today" | "preview"
  ) {
    const match = findLoggedFixture(fixture, goals);
    const live = isFixtureLive(fixture.kickoff, Date.now(), gradedKeys, fixture);
    if (match) {
      return (
        <MatchCard
          key={fixture.fixtureId}
          match={match}
          detail={matchDetails[match.fixtureId] ?? null}
          index={index}
          emphasis={emphasis}
          live={live}
        />
      );
    }
    return (
      <PreviewMatchCard
        key={fixture.fixtureId}
        fixture={fixture}
        watchlist={watchlistForFixture(watchlists, fixture)}
        index={index}
        emphasis={emphasis}
        live={live}
      />
    );
  }

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Goals: Over/Under 2.5</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Fixtures move Preview → Today → Past by kickoff time. Confirmed-lineup
        model fills in once XIs are announced (~20–40 min pre-kickoff).
      </p>

      <FixtureTimelineSection
        title="Today"
        description="Matches kicking off today (UTC), including live games until full-time. Goals O/U analysis when lineups are confirmed."
        emptyMessage="No Premier League matches scheduled for today."
        count={timeline.today.length}
        variant="today"
      >
        {timeline.today.map((f, i) => renderFixture(f, i, "today"))}
      </FixtureTimelineSection>

      <FixtureTimelineSection
        title="Preview"
        description={`Next ${UPCOMING_DISPLAY_LIMIT} scheduled fixtures on future matchdays.`}
        emptyMessage="No further fixtures in the preview window."
        count={timeline.preview.length}
        variant="preview"
      >
        {timeline.preview.map((f, i) => renderFixture(f, i, "preview"))}
      </FixtureTimelineSection>

      <PastDisclosure count={past.length}>
        {past.map((g, i) => (
          <MatchCard
            key={g.fixtureId}
            match={g}
            detail={matchDetails[g.fixtureId] ?? null}
            graded={findGradedResult(g, graded)}
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
  const gradedKeys = buildGradedKeys(graded);
  const timeline = buildFixtureTimeline(
    upcomingFixtures,
    goals,
    UPCOMING_DISPLAY_LIMIT,
    Date.now(),
    gradedKeys
  );
  const upcomingProps = props.filter((p) =>
    isActivePropsFixture(p.fixtureId, p.kickoff, timeline, goals, gradedKeys)
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
            timeline={timeline}
            watchlists={watchlists}
            graded={graded}
          />
        }
        props={
          <PropsPanel
            props={props}
            mostProbable={mostProbable}
            timeline={timeline}
            watchlists={watchlists}
            loggedGoals={goals}
            graded={graded}
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
