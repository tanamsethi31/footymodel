import {
  getPropsPicks,
  getMatchDetails,
  getUpcomingFixtures,
  getWatchlists,
  getMostProbablePicks,
  getGradedPropsFixtures,
  getGradedPropsPlayers,
  getPaperBankrollSummary,
  type PaperBankrollSummary,
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
import { pct } from "@/lib/format";

export const revalidate = 60;

function TrackRecordPanel({
  gradedFixtures,
  gradedPlayers,
  liveFixtureCount,
  paperBankroll,
}: {
  gradedFixtures: Awaited<ReturnType<typeof getGradedPropsFixtures>>;
  gradedPlayers: Awaited<ReturnType<typeof getGradedPropsPlayers>>;
  liveFixtureCount: number;
  paperBankroll: PaperBankrollSummary | null;
}) {
  const withActuals = gradedPlayers.filter((g) => g.actualShots !== null);
  const shotsHits = withActuals.filter((g) => g.shots1PlusHit).length;
  const sotHits = withActuals.filter((g) => g.sot1PlusHit).length;
  const shotsRate = withActuals.length ? shotsHits / withActuals.length : null;
  const sotRate = withActuals.length ? sotHits / withActuals.length : null;

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Track record</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Player shots/SOT props graded against Understat match stats when rosters
        are available; otherwise proxy XI from recent appearances. Internal
        €100 paper bankroll (SofaScore path only). Kickoffs in Irish time.
      </p>
      {paperBankroll && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="rounded-xl border border-blue-200 dark:border-blue-900/50 bg-blue-50/50 dark:bg-blue-950/20 p-4">
            <div className="text-neutral-500 text-xs">Paper bankroll</div>
            <div className="text-xl font-mono mt-1">
              €{paperBankroll.bankroll.toFixed(2)}
            </div>
            <div className="text-xs text-neutral-400">
              started €{paperBankroll.startingBankroll.toFixed(0)}
            </div>
          </div>
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
            <div className="text-neutral-500 text-xs">Open paper bets</div>
            <div className="text-xl font-mono mt-1">{paperBankroll.openBets}</div>
          </div>
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
            <div className="text-neutral-500 text-xs">Won / lost</div>
            <div className="text-xl font-mono mt-1">
              {paperBankroll.wonBets} / {paperBankroll.lostBets}
            </div>
          </div>
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 sm:col-span-1 col-span-2">
            <div className="text-neutral-500 text-xs">Live scope</div>
            <div className="text-sm mt-1 text-neutral-600 dark:text-neutral-300">
              PL player shots &amp; SOT · SofaScore lineups
            </div>
          </div>
        </div>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
          <div className="text-neutral-500 text-xs">Graded fixtures</div>
          <div className="text-xl font-mono mt-1">{gradedFixtures.length}</div>
        </div>
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
          <div className="text-neutral-500 text-xs">Live-logged fixtures</div>
          <div className="text-xl font-mono mt-1">{liveFixtureCount}</div>
        </div>
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
          <div className="text-neutral-500 text-xs">Shots 1+ hit rate</div>
          <div className="text-xl font-mono mt-1">{pct(shotsRate)}</div>
          <div className="text-xs text-neutral-400">{withActuals.length} player-rows</div>
        </div>
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4">
          <div className="text-neutral-500 text-xs">SOT 1+ hit rate</div>
          <div className="text-xl font-mono mt-1">{pct(sotRate)}</div>
        </div>
      </div>
      {gradedFixtures.length === 0 && (
        <p className="text-sm text-neutral-500">
          Run <code className="text-xs">scripts/backfill_recent_props.py</code> or the
          live SofaScore poll to populate graded history.
        </p>
      )}
    </section>
  );
}

export default async function Home() {
  const [props, matchDetails, upcomingFixtures, watchlists, gradedFixtures, gradedPlayers, paperBankroll] =
    await Promise.all([
      getPropsPicks(),
      getMatchDetails(),
      getUpcomingFixtures(),
      getWatchlists(),
      getGradedPropsFixtures(),
      getGradedPropsPlayers(),
      getPaperBankrollSummary(),
    ]);

  const loggedFixtures = buildLoggedFixturesFromProps(props, upcomingFixtures);
  const gradedKeys = buildGradedKeys(
    gradedFixtures.map((g) => ({
      fixtureId: g.fixtureId,
      home: g.home,
      away: g.away,
      kickoff: g.kickoff,
    }))
  );
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
  const liveFixtureCount = new Set(props.map((p) => p.fixtureId)).size;

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 sm:py-14 w-full">
      <header className="flex flex-row items-start justify-between gap-4 mb-10">
        <div className="min-w-0 flex-1">
          <Logo />
          <p className="text-sm text-neutral-500 mt-1">
            Premier League player shots and shots-on-target — confirmed-lineup
            models, SofaScore-only live path, €100 internal paper bankroll.
            Irish time. Not real betting.
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
            gradedFixtures={gradedFixtures}
            gradedPlayers={gradedPlayers}
          />
        }
        trackRecord={
          <TrackRecordPanel
            gradedFixtures={gradedFixtures}
            gradedPlayers={gradedPlayers}
            liveFixtureCount={liveFixtureCount}
            paperBankroll={paperBankroll}
          />
        }
        features={<FeaturesPanel />}
        glossary={<GlossaryPanel />}
      />

      <footer className="mt-16 text-xs text-neutral-400">
        Research project — PL player shots/SOT only. Paper-trade (€100 internal
        ledger). SofaScore on home Wi‑Fi for live polls. Kickoffs: Europe/Dublin.
      </footer>
    </div>
  );
}
