import type { GradedPropsFixture, GradedPropsPlayer } from "@/lib/data";
import { formatKickoff, pct } from "@/lib/format";

export default function PropsPastSummary({
  fixture,
  grades,
}: {
  fixture: GradedPropsFixture;
  grades: GradedPropsPlayer[];
}) {
  const withShots = grades.filter((g) => g.actualShots !== null);
  const withSot = grades.filter((g) => g.actualSot !== null);
  const shotsHits = withShots.filter((g) => g.shots1PlusHit === true).length;
  const sotHits = withSot.filter((g) => g.sot1PlusHit === true).length;
  const shotsRate = withShots.length ? shotsHits / withShots.length : null;
  const sotRate = withSot.length ? sotHits / withSot.length : null;

  return (
    <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-50/80 dark:bg-neutral-900/40 px-4 py-3 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-medium">
          {fixture.home} {fixture.homeGoals}-{fixture.awayGoals} {fixture.away}
        </span>
        <span className="text-xs text-neutral-500">{formatKickoff(fixture.kickoff)}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-600 dark:text-neutral-400">
        {fixture.homeShots !== null && fixture.awayShots !== null && (
          <span>
            Team shots {fixture.homeShots}-{fixture.awayShots} (football-data)
          </span>
        )}
        {fixture.proxyXi && (
          <span className="text-amber-700 dark:text-amber-400">
            Proxy XI (Understat roster not published yet)
          </span>
        )}
        {fixture.understatMatchId && (
          <span>Understat match {fixture.understatMatchId}</span>
        )}
        {withShots.length > 0 && (
          <span>
            Shots 1+ hit rate: {shotsHits}/{withShots.length} ({pct(shotsRate)})
            {withSot.length > 0 && (
              <>
                {" "}
                · SOT 1+: {sotHits}/{withSot.length} ({pct(sotRate)})
              </>
            )}
          </span>
        )}
      </div>
    </div>
  );
}
