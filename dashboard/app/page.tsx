import {
  getPropsPicks,
  getMatchDetails,
  getUpcomingFixtures,
  getWatchlists,
  getMostProbablePicks,
} from "@/lib/data";
import { buildFixtureTimeline } from "@/lib/fixtureTimeline";
import { buildGradedKeys } from "@/lib/graded";
import { buildLoggedFixturesFromProps } from "@/lib/propsFixtures";
import { UPCOMING_DISPLAY_LIMIT } from "@/lib/upcoming";
import Logo from "@/components/Logo";
import SubscribeButton from "@/components/SubscribeButton";
import RefreshButton from "@/components/RefreshButton";
import ThemeToggle from "@/components/ThemeToggle";
import DashboardTabs from "@/components/DashboardTabs";
import PropsPanel, { isActivePropsFixture } from "@/components/PropsPanel";
import GlossaryPanel from "@/components/GlossaryPanel";
import FeaturesPanel from "@/components/FeaturesPanel";

export const revalidate = 60;

function TrackRecordPanel({ fixtureCount }: { fixtureCount: number }) {
  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Track record</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Forward paper-trade for player shots and shots-on-target props. Historical
        prop odds are not archived, so live rows are graded against real match
        stats as that pipeline ships (WhoScored/FBref post-match ingest).
      </p>
      <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-6 text-sm text-neutral-600 dark:text-neutral-400 space-y-3">
        <p>
          <span className="font-mono text-lg text-neutral-900 dark:text-neutral-100">
            {fixtureCount}
          </span>{" "}
          fixture(s) with logged player-prop lines in this dataset so far.
        </p>
        <p>
          Win rate, calibration, and CLV for props will appear here once automated
          grading lands. Goals O/U track record is retired — this project is
          props-only now.
        </p>
      </div>
    </section>
  );
}

export default async function Home() {
  const [props, matchDetails, upcomingFixtures, watchlists] = await Promise.all([
    getPropsPicks(),
    getMatchDetails(),
    getUpcomingFixtures(),
    getWatchlists(),
  ]);

  const loggedFixtures = buildLoggedFixturesFromProps(props, upcomingFixtures);
  const gradedKeys = buildGradedKeys([]);
  const timeline = buildFixtureTimeline(
    upcomingFixtures,
    loggedFixtures,
    UPCOMING_DISPLAY_LIMIT,
    Date.now(),
    gradedKeys
  );
  const upcomingProps = props.filter((p) =>
    isActivePropsFixture(p.fixtureId, p.kickoff, timeline, loggedFixtures, gradedKeys)
  );
  const mostProbable = getMostProbablePicks(upcomingProps);
  const fixtureCount = new Set(props.map((p) => p.fixtureId)).size;

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 sm:py-14 w-full">
      <header className="flex flex-row items-start justify-between gap-4 mb-10">
        <div className="min-w-0 flex-1">
          <Logo />
          <p className="text-sm text-neutral-500 mt-1">
            Premier League player shots and shots-on-target — walk-forward
            calibrated models, confirmed-lineup updates, optional book odds when
            available. Paper-trade only.
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
        predictions={
          <PropsPanel
            props={props}
            mostProbable={mostProbable}
            timeline={timeline}
            watchlists={watchlists}
            matchDetails={matchDetails}
            loggedFixtures={loggedFixtures}
          />
        }
        trackRecord={<TrackRecordPanel fixtureCount={fixtureCount} />}
        features={<FeaturesPanel />}
        glossary={<GlossaryPanel />}
      />

      <footer className="mt-16 text-xs text-neutral-400">
        Research project. Paper-trade only. Data refreshes about every minute;
        tap ↻ to pull the latest from GitHub (once per minute). Enable
        notifications to get a push when new prop lines are logged.
      </footer>
    </div>
  );
}
