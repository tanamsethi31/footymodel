import type { ReactNode } from "react";
import {
  sectionTodayBadgeClass,
  sectionTodayClass,
  sectionTodayDescriptionClass,
  sectionTodayEmptyClass,
  sectionTodayTitleClass,
} from "@/lib/timelineStyles";

export type TimelineSectionVariant = "today" | "preview";

export default function FixtureTimelineSection({
  title,
  description,
  emptyMessage,
  count,
  variant = "preview",
  children,
}: {
  title: string;
  description: string;
  emptyMessage?: string;
  count: number;
  variant?: TimelineSectionVariant;
  children: ReactNode;
}) {
  const isToday = variant === "today";

  return (
    <section className={`mb-8 last:mb-0 ${isToday ? sectionTodayClass() : ""}`}>
      <div className={`mb-3 ${isToday ? "" : "opacity-90"}`}>
        <div className="flex items-center gap-2 flex-wrap">
          <h3
            className={`font-semibold ${
              isToday ? sectionTodayTitleClass() : "text-sm text-neutral-700 dark:text-neutral-300"
            }`}
          >
            {title}
          </h3>
          {isToday && <span className={sectionTodayBadgeClass()}>Match day</span>}
          {!isToday && count > 0 && (
            <span className="text-[10px] uppercase tracking-wide text-neutral-400">
              Upcoming
            </span>
          )}
        </div>
        <p className={`mt-0.5 ${isToday ? sectionTodayDescriptionClass() : "text-xs text-neutral-500"}`}>
          {description}
        </p>
      </div>
      {count === 0 ? (
        emptyMessage ? (
          <p className={isToday ? sectionTodayEmptyClass() : "text-sm text-neutral-500"}>
            {emptyMessage}
          </p>
        ) : null
      ) : (
        <div className={`space-y-3 ${isToday ? "" : "pl-0.5"}`}>{children}</div>
      )}
    </section>
  );
}
