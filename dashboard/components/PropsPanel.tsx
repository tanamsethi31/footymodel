import {
  buildFixtureTimeline,
  findLoggedFixture,
  kickoffMs,
  sortPastByKickoff,
  type FixtureTimeline,
} from "@/lib/fixtureTimeline";
import type { FixtureWatchlist, GoalsPick, PropsPick, MostProbablePick, UpcomingFixture } from "@/lib/data";
import { UPCOMING_DISPLAY_LIMIT, watchlistForFixture } from "@/lib/upcoming";
import FixtureTimelineSection from "./FixtureTimelineSection";
import MostProbableStrip from "./MostProbableStrip";
import MatchPropsTable from "./MatchPropsTable";
import PastDisclosure from "./PastDisclosure";
import PropsPreviewCard from "./PropsPreviewCard";

function buildPropsIndex(props: PropsPick[]) {
  const byFixtureId = new Map<string, PropsPick[]>();
  for (const p of props) {
    const arr = byFixtureId.get(p.fixtureId) ?? [];
    arr.push(p);
    byFixtureId.set(p.fixtureId, arr);
  }
  return byFixtureId;
}

function findPropsRows(
  fixture: UpcomingFixture,
  byFixtureId: Map<string, PropsPick[]>,
  loggedGoals: GoalsPick[]
): PropsPick[] | undefined {
  const direct = byFixtureId.get(fixture.fixtureId);
  if (direct?.length) return direct;
  const goal = findLoggedFixture(fixture, loggedGoals);
  if (goal) {
    const viaGoal = byFixtureId.get(goal.fixtureId);
    if (viaGoal?.length) return viaGoal;
  }
  return undefined;
}

export function isActivePropsFixture(
  fixtureId: string,
  kickoff: string,
  timeline: FixtureTimeline,
  loggedGoals: GoalsPick[]
): boolean {
  if (kickoffMs(kickoff) <= Date.now()) return false;
  const inBucket = (list: UpcomingFixture[]) =>
    list.some((f) => {
      if (f.fixtureId === fixtureId) return true;
      const goal = findLoggedFixture(f, loggedGoals);
      return goal?.fixtureId === fixtureId;
    });
  return inBucket(timeline.today) || inBucket(timeline.preview);
}

export default function PropsPanel({
  props,
  mostProbable,
  timeline,
  watchlists,
  loggedGoals,
}: {
  props: PropsPick[];
  mostProbable: MostProbablePick[];
  timeline: FixtureTimeline;
  watchlists: FixtureWatchlist[];
  loggedGoals: GoalsPick[];
}) {
  const now = Date.now();
  const byFixtureId = buildPropsIndex(props);

  const pastGroups = sortPastByKickoff(
    [...byFixtureId.entries()]
      .filter(([, rows]) => kickoffMs(rows[0].kickoff) <= now)
      .map(([fixtureId, rows]) => ({ fixtureId, rows, kickoff: rows[0].kickoff }))
  ).map(({ fixtureId, rows }) => [fixtureId, rows] as [string, PropsPick[]]);

  function renderFixture(fixture: UpcomingFixture, index: number) {
    const rows = findPropsRows(fixture, byFixtureId, loggedGoals);
    if (rows && rows.length > 0) {
      return <MatchPropsTable key={fixture.fixtureId} fixtureId={fixture.fixtureId} rows={rows} />;
    }
    return (
      <PropsPreviewCard
        key={fixture.fixtureId}
        fixture={fixture}
        watchlist={watchlistForFixture(watchlists, fixture)}
        index={index}
      />
    );
  }

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Player shots &amp; shots-on-target</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Fixtures move Preview → Today → Past as kickoff approaches. Player lines
        fill in once lineups are confirmed (~20–40 min pre-kickoff). SOT 3+ has
        no underlying data yet, shown as -.
      </p>

      <MostProbableStrip picks={mostProbable} />

      <FixtureTimelineSection
        title="Today"
        description="Matches kicking off today (UTC). Full XI and shots/SOT 1+/2+/3+ analysis appears once lineups are confirmed."
        emptyMessage="No Premier League matches scheduled for today."
        count={timeline.today.length}
      >
        {timeline.today.map((f, i) => renderFixture(f, i))}
      </FixtureTimelineSection>

      <FixtureTimelineSection
        title="Preview"
        description={`Next ${UPCOMING_DISPLAY_LIMIT} scheduled fixtures on future matchdays.`}
        emptyMessage="No further fixtures in the preview window."
        count={timeline.preview.length}
      >
        {timeline.preview.map((f, i) => renderFixture(f, i))}
      </FixtureTimelineSection>

      <PastDisclosure count={pastGroups.length}>
        {pastGroups.map(([fixtureId, rows]) => (
          <MatchPropsTable key={fixtureId} fixtureId={fixtureId} rows={rows} />
        ))}
      </PastDisclosure>
    </section>
  );
}
