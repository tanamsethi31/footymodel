import type { PropsPick, MostProbablePick, UpcomingFixture } from "@/lib/data";
import MostProbableStrip from "./MostProbableStrip";
import MatchPropsTable from "./MatchPropsTable";
import PastDisclosure from "./PastDisclosure";
import PreviewMatchCard from "./PreviewMatchCard";

export default function PropsPanel({
  props,
  mostProbable,
  upcomingFixtures,
}: {
  props: PropsPick[];
  mostProbable: MostProbablePick[];
  upcomingFixtures: UpcomingFixture[];
}) {
  const propsByFixture = new Map<string, PropsPick[]>();
  for (const p of props) {
    const arr = propsByFixture.get(p.fixtureId) ?? [];
    arr.push(p);
    propsByFixture.set(p.fixtureId, arr);
  }

  // A fixture's rows all share the same kickoff, so any row's kickoff tells
  // us whether the whole group is upcoming or already played.
  const now = Date.now();
  const groups = [...propsByFixture.entries()];
  const upcomingGroups = groups
    .filter(([, rows]) => new Date(rows[0].kickoff).getTime() > now)
    .sort((a, b) => new Date(a[1][0].kickoff).getTime() - new Date(b[1][0].kickoff).getTime());
  const pastGroups = groups.filter(([, rows]) => new Date(rows[0].kickoff).getTime() <= now);
  // Any upcoming fixture without prop rows yet shows as a preview card -
  // once its lineup is confirmed it'll show up in propsByFixture above and
  // drop out of this list automatically.
  const previewFixtures = upcomingFixtures
    .filter((f) => !propsByFixture.has(f.fixtureId) && new Date(f.kickoff).getTime() > now)
    .sort((a, b) => new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime());

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Player shots &amp; shots-on-target</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Well-calibrated in backtesting (gaps within ±0.03). Live profit untested,
        no historical prop-odds archive exists to backtest against. SOT 3+ has no
        underlying data yet, shown as -.
      </p>

      <MostProbableStrip picks={mostProbable} />

      {propsByFixture.size === 0 && previewFixtures.length === 0 ? (
        <p className="text-sm text-neutral-500">No prop predictions logged yet.</p>
      ) : upcomingGroups.length === 0 && previewFixtures.length === 0 ? (
        <p className="text-sm text-neutral-500">No upcoming prop predictions right now.</p>
      ) : (
        <div className="space-y-4">
          {upcomingGroups.map(([fixtureId, rows]) => (
            <MatchPropsTable key={fixtureId} fixtureId={fixtureId} rows={rows} />
          ))}
          {previewFixtures.map((f, i) => (
            <PreviewMatchCard
              key={f.fixtureId}
              fixture={f}
              index={upcomingGroups.length + i}
            />
          ))}
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
