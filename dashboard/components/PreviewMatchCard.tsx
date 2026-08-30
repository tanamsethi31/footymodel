import type { UpcomingFixture } from "@/lib/data";
import { formatKickoff } from "@/lib/format";

export default function PreviewMatchCard({
  fixture,
  index,
}: {
  fixture: UpcomingFixture;
  index: number;
}) {
  return (
    <div
      className="animate-stagger-in rounded-xl border border-neutral-200 dark:border-neutral-800 p-4"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className="font-medium">
          {fixture.home} v {fixture.away}
        </span>
        <span className="text-xs text-neutral-500">{formatKickoff(fixture.kickoff)}</span>
      </div>
      <p className="mt-3 text-xs text-neutral-400">
        Analysis available once lineups are confirmed (~20-40min pre-kickoff).
      </p>
    </div>
  );
}
