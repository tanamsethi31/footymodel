import type { PropsPick, MostProbablePick } from "@/lib/data";
import MostProbableStrip from "./MostProbableStrip";
import MatchPropsTable from "./MatchPropsTable";

export default function PropsPanel({
  props,
  mostProbable,
}: {
  props: PropsPick[];
  mostProbable: MostProbablePick[];
}) {
  const propsByFixture = new Map<string, PropsPick[]>();
  for (const p of props) {
    const arr = propsByFixture.get(p.fixtureId) ?? [];
    arr.push(p);
    propsByFixture.set(p.fixtureId, arr);
  }

  return (
    <section>
      <h2 className="text-lg font-semibold mb-1">Player shots &amp; shots-on-target</h2>
      <p className="text-sm text-neutral-500 mb-5">
        Well-calibrated in backtesting (gaps within ±0.03). Live profit untested,
        no historical prop-odds archive exists to backtest against. SOT 3+ has no
        underlying data yet, shown as -.
      </p>

      <MostProbableStrip picks={mostProbable} />

      {propsByFixture.size === 0 ? (
        <p className="text-sm text-neutral-500">No prop predictions logged yet.</p>
      ) : (
        <div className="space-y-4">
          {[...propsByFixture.entries()].map(([fixtureId, rows]) => (
            <MatchPropsTable key={fixtureId} fixtureId={fixtureId} rows={rows} />
          ))}
        </div>
      )}
    </section>
  );
}
