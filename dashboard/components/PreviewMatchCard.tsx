import type { UpcomingFixture } from "@/lib/data";
import { formatKickoff } from "@/lib/format";

export default function PreviewMatchCard({
  fixture,
  index,
  pendingLabel = "Analysis available once lineups are confirmed (~20-40min pre-kickoff).",
}: {
  fixture: UpcomingFixture;
  index: number;
  pendingLabel?: string;
}) {
  return (
    <div
      className="animate-stagger-in rounded-xl border border-dashed border-neutral-300 dark:border-neutral-700 p-4"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className="font-medium">
          {fixture.home} v {fixture.away}
        </span>
        <span className="text-xs text-neutral-500">{formatKickoff(fixture.kickoff)}</span>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-wide font-medium text-neutral-500 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700 rounded-full px-2 py-0.5">
          Preview
        </span>
        <p className="text-xs text-neutral-400">{pendingLabel}</p>
      </div>
    </div>
  );
}
