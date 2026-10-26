import {
  buildFixtureTimeline,
  findLoggedFixture,
  isFixtureFinished,
  isFixtureLive,
  type FixtureTimeline,
} from "@/lib/fixtureTimeline";
import type {
  FixtureWatchlist,
  GradedPropsFixture,
  GradedPropsPlayer,
  MatchDetail,
  PropsPick,
  MostProbablePick,
  UpcomingFixture,
} from "@/lib/data";
import PropsPastSummary from "./PropsPastSummary";
import { UPCOMING_DISPLAY_LIMIT, watchlistForFixture } from "@/lib/upcoming";
import { buildGradedKeys, sortPastPredictions } from "@/lib/graded";
import { propsRowsFromGrades } from "@/lib/propsGrading";
import type { LoggedFixture } from "@/lib/propsFixtures";
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
  logged: LoggedFixture[]
): PropsPick[] | undefined {
  const direct = byFixtureId.get(fixture.fixtureId);
  if (direct?.length) return direct;
  const match = findLoggedFixture(fixture, logged);
  if (match) {
    const via = byFixtureId.get(match.fixtureId);
    if (via?.length) return via;
  }
  return undefined;
}

export function isActivePropsFixture(
  fixtureId: string,
  kickoff: string,
  timeline: FixtureTimeline,
  logged: LoggedFixture[],
  gradedKeys: Set<string>
): boolean {
  const ref = logged.find((g) => g.fixtureId === fixtureId);
  const timelineFixture =
    [...timeline.today, ...timeline.preview].find((f) => f.fixtureId === fixtureId) ??
    (ref
      ? [...timeline.today, ...timeline.preview].find(
          (f) => findLoggedFixture(f, [ref]) !== undefined
        )
      : undefined);
  const fixtureRef = ref ?? timelineFixture;
  if (
    isFixtureFinished(
      kickoff,
      Date.now(),
      gradedKeys,
      fixtureRef
        ? {
            fixtureId: fixtureRef.fixtureId,
            home: fixtureRef.home,
            away: fixtureRef.away,
            kickoff: fixtureRef.kickoff,
          }
        : { fixtureId, home: "", away: "", kickoff }
    )
  ) {
    return false;
  }
  const inBucket = (list: UpcomingFixture[]) =>
    list.some((f) => {
      if (f.fixtureId === fixtureId) return true;
      const m = findLoggedFixture(f, logged);
      return m?.fixtureId === fixtureId;
    });
  return inBucket(timeline.today) || inBucket(timeline.preview);
}

export default function PropsPanel({
  props,
  mostProbable,
  timeline,
  watchlists,
  matchDetails,
  loggedFixtures,
  gradedFixtures,
  gradedPlayers,
}: {
  props: PropsPick[];
  mostProbable: MostProbablePick[];
  timeline: FixtureTimeline;
  watchlists: FixtureWatchlist[];
  matchDetails: Record<string, MatchDetail>;
  loggedFixtures: LoggedFixture[];
  gradedFixtures: GradedPropsFixture[];
  gradedPlayers: GradedPropsPlayer[];
}) {
  const now = Date.now();
  const gradedKeys = buildGradedKeys(
    gradedFixtures.map((g) => ({
      fixtureId: g.fixtureId,
      home: g.home,
      away: g.away,
      kickoff: g.kickoff,
    }))
  );
  const byFixtureId = buildPropsIndex(props);

  const plLogged = loggedFixtures.filter(
    (f) => f.home && f.away // PL-only pipeline; all logged props are E0
  );

  const gradesByFixture = new Map<string, GradedPropsPlayer[]>();
  for (const g of gradedPlayers) {
    const arr = gradesByFixture.get(g.fixtureId) ?? [];
    arr.push(g);
    gradesByFixture.set(g.fixtureId, arr);
  }

  const pastFromGraded = gradedFixtures.map((gf) => {
    const rows = byFixtureId.get(gf.fixtureId) ?? [];
    const logged: LoggedFixture = {
      fixtureId: gf.fixtureId,
      home: gf.home,
      away: gf.away,
      kickoff: gf.kickoff,
    };
    return { gf, logged, rows };
  });

  const pastFixtures = sortPastPredictions(
    plLogged.filter((f) => isFixtureFinished(f.kickoff, now, gradedKeys, f))
  );

  const pastGroupsLegacy = pastFixtures
    .filter((f) => !gradedFixtures.some((g) => g.fixtureId === f.fixtureId))
    .map((f) => {
      const rows = byFixtureId.get(f.fixtureId);
      return rows ? ([f, rows] as [LoggedFixture, PropsPick[]]) : null;
    })
    .filter((entry): entry is [LoggedFixture, PropsPick[]] => entry !== null);

  function renderFixture(
    fixture: UpcomingFixture,
    index: number,
    emphasis: "today" | "preview"
  ) {
    const rows = findPropsRows(fixture, byFixtureId, plLogged);
    const live = isFixtureLive(fixture.kickoff, now, gradedKeys, fixture);
    const detail = matchDetails[fixture.fixtureId] ?? null;
    if (rows && rows.length > 0) {
      return (
        <MatchPropsTable
          key={fixture.fixtureId}
          fixtureId={fixture.fixtureId}
          home={fixture.home}
          away={fixture.away}
          rows={rows}
          lineup={detail}
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
        Premier League player props. Fixtures move Preview → Today →
        Past; confirmed XIs and prop lines land ~20–40 minutes before kickoff via
        SofaScore on home Wi‑Fi. Internal €100 paper ledger sizes stakes after each
        poll. Research only, not betting advice.
      </p>

      <MostProbableStrip picks={mostProbable} />

      <FixtureTimelineSection
        title="Today"
        description="Matches kicking off today (Irish time). Live until full-time. Confirmed lineups and shots/SOT model output when the poll catches the XI window."
        emptyMessage="No Premier League matches scheduled for today."
        count={timeline.today.length}
        variant="today"
      >
        {timeline.today.map((f, i) => renderFixture(f, i, "today"))}
      </FixtureTimelineSection>

      <FixtureTimelineSection
        title="Upcoming"
        description={`Next ${UPCOMING_DISPLAY_LIMIT} scheduled fixtures on future matchdays — pre-match watchlists and kickoff times.`}
        emptyMessage="No further fixtures in the preview window."
        count={timeline.preview.length}
        variant="preview"
      >
        {timeline.preview.map((f, i) => renderFixture(f, i, "preview"))}
      </FixtureTimelineSection>

      <PastDisclosure count={pastFromGraded.length + pastGroupsLegacy.length}>
        {pastFromGraded.map(({ gf, logged, rows }) => {
          const grades = gradesByFixture.get(gf.fixtureId) ?? [];
          const gradeMap = new Map(grades.map((g) => [g.player, g]));
          const displayRows =
            rows.length > 0 ? rows : propsRowsFromGrades(gf, grades);
          return (
            <div key={gf.fixtureId} className="space-y-2">
              <PropsPastSummary fixture={gf} grades={grades} />
              <MatchPropsTable
                fixtureId={gf.fixtureId}
                home={logged.home}
                away={logged.away}
                rows={displayRows}
                lineup={matchDetails[gf.fixtureId] ?? null}
                playerGrades={gradeMap}
                emphasis="past"
              />
            </div>
          );
        })}
        {pastGroupsLegacy.map(([fixture, rows]) => (
          <div key={fixture.fixtureId} className="space-y-2">
            <MatchPropsTable
              fixtureId={fixture.fixtureId}
              home={fixture.home}
              away={fixture.away}
              rows={rows}
              lineup={matchDetails[fixture.fixtureId] ?? null}
            />
          </div>
        ))}
      </PastDisclosure>
    </section>
  );
}
