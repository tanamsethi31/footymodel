import type { FixtureWatchlist, PropsPick, MostProbablePick, UpcomingFixture } from "@/lib/data";
import { UPCOMING_DISPLAY_LIMIT, watchlistForFixture } from "@/lib/upcoming";
import MostProbableStrip from "./MostProbableStrip";
import MatchPropsTable from "./MatchPropsTable";
import PastDisclosure from "./PastDisclosure";
import PropsPreviewCard from "./PropsPreviewCard";

export default function PropsPanel({
  props,
  mostProbable,
  nextFixtures,
  watchlists,
}: {
  props: PropsPick[];
  mostProbable: MostProbablePick[];
  nextFixtures: UpcomingFixture[];
  watchlists: FixtureWatchlist[];
}) {
  const propsByFixture = new Map<string, PropsPick[]>();
  for (const p of props) {
    const arr = propsByFixture.get(p.fixtureId) ?? [];
    arr.push(p);
    propsByFixture.set(p.fixtureId, arr);
  }

  const now = Date.now();
  const groups = [...propsByFixture.entries()];
  const pastGroups = groups.filter(([, rows]) => new Date(rows[0].kickoff).getTime() <= now);

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Player shots &amp; shots-on-target</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Same next {UPCOMING_DISPLAY_LIMIT} fixtures as Goals, kickoff order.
        Player lines fill in once lineups are confirmed. Well-calibrated in
        backtesting (gaps within ±0.03). SOT 3+ has no underlying data yet,
        shown as -.
      </p>

      <MostProbableStrip picks={mostProbable} />

      {nextFixtures.length === 0 ? (
        <p className="text-sm text-neutral-500">No upcoming Premier League fixtures in the current window.</p>
      ) : (
        <div className="space-y-4">
          {nextFixtures.map((f, i) => {
            const rows = propsByFixture.get(f.fixtureId);
            if (rows && rows.length > 0) {
              return <MatchPropsTable key={f.fixtureId} fixtureId={f.fixtureId} rows={rows} />;
            }
            return (
              <PropsPreviewCard
                key={f.fixtureId}
                fixture={f}
                watchlist={watchlistForFixture(watchlists, f)}
                index={i}
              />
            );
          })}
        </div>
      )}
      <PastDisclosure count={pastGroups.length}>
        {pastGroups.map(([fixtureId, rows]) => (
          <MatchPropsTable key={fixtureId} fixtureId={fixtureId} rows={rows} />
        ))}
      </PastDisclosure>
    </section>
  );
}
