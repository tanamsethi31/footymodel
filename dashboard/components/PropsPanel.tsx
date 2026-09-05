import {
  buildFixtureTimeline,
  findLoggedFixture,
  isFixtureFinished,
  isFixtureLive,
  type FixtureTimeline,
} from "@/lib/fixtureTimeline";
import type { FixtureWatchlist, GoalsPick, PropsPick, MostProbablePick, UpcomingFixture, GradedResult } from "@/lib/data";
import { UPCOMING_DISPLAY_LIMIT, watchlistForFixture } from "@/lib/upcoming";
import { buildGradedKeys, findGradedResult, sortPastPredictions } from "@/lib/graded";
import { PREMIER_LEAGUE } from "@/lib/league";
import PredictionResultBanner from "./PredictionResultBanner";
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
  loggedGoals: GoalsPick[],
  gradedKeys: Set<string>
): boolean {
  const goal = loggedGoals.find((g) => g.fixtureId === fixtureId);
  const timelineFixture =
    [...timeline.today, ...timeline.preview].find((f) => f.fixtureId === fixtureId) ??
    (goal
      ? [...timeline.today, ...timeline.preview].find(
          (f) => findLoggedFixture(f, [goal]) !== undefined
        )
      : undefined);
  const ref = goal ?? timelineFixture;
  if (
    isFixtureFinished(
      kickoff,
      Date.now(),
      gradedKeys,
      ref
        ? {
            fixtureId: ref.fixtureId,
            home: ref.home,
            away: ref.away,
            kickoff: ref.kickoff,
          }
        : { fixtureId, home: "", away: "", kickoff }
    )
  ) {
    return false;
  }
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
  graded,
}: {
  props: PropsPick[];
  mostProbable: MostProbablePick[];
  timeline: FixtureTimeline;
  watchlists: FixtureWatchlist[];
  loggedGoals: GoalsPick[];
  graded: GradedResult[];
}) {
  const now = Date.now();
  const gradedKeys = buildGradedKeys(graded);
  const byFixtureId = buildPropsIndex(props);

  const plGoals = loggedGoals.filter((g) => g.league === PREMIER_LEAGUE);
  const plFixtureIds = new Set(plGoals.map((g) => g.fixtureId));

  const pastEntries = [...byFixtureId.entries()].filter(([fixtureId, rows]) => {
    if (!plFixtureIds.has(fixtureId)) return false;
    const goal = plGoals.find((g) => g.fixtureId === fixtureId);
    if (!goal) return false;
    return isFixtureFinished(rows[0].kickoff, now, gradedKeys, goal);
  });

  const pastGoals = sortPastPredictions(
    pastEntries.map(([fixtureId]) => plGoals.find((g) => g.fixtureId === fixtureId)!)
  );

  const pastGroups = pastGoals
    .map((goal) => {
      const rows = byFixtureId.get(goal.fixtureId);
      return rows ? ([goal.fixtureId, rows] as [string, PropsPick[]]) : null;
    })
    .filter((entry): entry is [string, PropsPick[]] => entry !== null);

  function renderFixture(
    fixture: UpcomingFixture,
    index: number,
    emphasis: "today" | "preview"
  ) {
    const rows = findPropsRows(fixture, byFixtureId, loggedGoals);
    const live = isFixtureLive(fixture.kickoff, now, gradedKeys, fixture);
    if (rows && rows.length > 0) {
      return (
        <MatchPropsTable
          key={fixture.fixtureId}
          fixtureId={fixture.fixtureId}
          rows={rows}
          emphasis={emphasis}
          live={live}
        />
      );
    }
    return (
      <PropsPreviewCard
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
      <h2 className="text-lg font-semibold mb-1">Player shots &amp; shots-on-target</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Fixtures move Preview → Today → Past as kickoff approaches. Player lines
        fill in once lineups are confirmed (~20–40 min pre-kickoff). SOT 3+ has
        no underlying data yet, shown as -.
      </p>

      <MostProbableStrip picks={mostProbable} />

      <FixtureTimelineSection
        title="Today"
        description="Matches kicking off today (UTC), including live games until full-time. Full XI and shots/SOT analysis once lineups are confirmed."
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

      <PastDisclosure count={pastGroups.length}>
        {pastGroups.map(([fixtureId, rows]) => {
          const goal = loggedGoals.find((g) => g.fixtureId === fixtureId);
          const gradedResult = goal ? findGradedResult(goal, graded) : null;

          return (
            <div key={fixtureId} className="space-y-2">
              {gradedResult && <PredictionResultBanner graded={gradedResult} />}
              <MatchPropsTable fixtureId={fixtureId} rows={rows} />
            </div>
          );
        })}
      </PastDisclosure>
    </section>
  );
}
