import type { UpcomingFixture } from "@/lib/data";
import { formatKickoff } from "@/lib/format";
import { emphasisBadge, previewCardEmphasisClass, type TimelineEmphasis } from "@/lib/timelineStyles";

export default function PreviewMatchCard({
  fixture,
  index,
  emphasis = "preview",
  pendingLabel = "Analysis available once lineups are confirmed (~20-40min pre-kickoff).",
}: {
  fixture: UpcomingFixture;
  index: number;
  emphasis?: TimelineEmphasis;
  pendingLabel?: string;
}) {
  const badge = emphasisBadge(emphasis);

  return (
    <div
      className={`animate-stagger-in rounded-xl border p-4 ${previewCardEmphasisClass(emphasis)}`}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className={`font-medium flex items-center gap-2 flex-wrap ${emphasis === "today" ? "text-blue-950 dark:text-blue-50" : ""}`}>
          {fixture.home} v {fixture.away}
          <span className={badge.className}>{badge.label}</span>
        </span>
        <span className={`text-xs ${emphasis === "today" ? "text-blue-700/80 dark:text-blue-300/80 font-medium" : "text-neutral-500"}`}>
          {formatKickoff(fixture.kickoff)}
        </span>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <p className={`text-xs ${emphasis === "today" ? "text-blue-800/70 dark:text-blue-200/70" : "text-neutral-400"}`}>
          {pendingLabel}
        </p>
      </div>
    </div>
  );
}
