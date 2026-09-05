import type { ReactNode } from "react";

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
    <section
      className={`mb-8 last:mb-0 ${
        isToday
          ? "rounded-2xl border-2 border-blue-200 dark:border-blue-800 bg-gradient-to-b from-blue-50/90 to-white dark:from-blue-950/35 dark:to-neutral-950 p-4 sm:p-5 shadow-sm"
          : ""
      }`}
    >
      <div className={`mb-3 ${isToday ? "" : "opacity-90"}`}>
        <div className="flex items-center gap-2 flex-wrap">
          <h3
            className={`font-semibold ${
              isToday
                ? "text-base text-blue-900 dark:text-blue-100"
                : "text-sm text-neutral-700 dark:text-neutral-300"
            }`}
          >
            {title}
          </h3>
          {isToday && (
            <span className="text-[10px] uppercase tracking-wider font-semibold text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-950 border border-blue-200 dark:border-blue-700 rounded-full px-2.5 py-0.5">
              Match day
            </span>
          )}
          {!isToday && count > 0 && (
            <span className="text-[10px] uppercase tracking-wide text-neutral-400">
              Upcoming
            </span>
          )}
        </div>
        <p
          className={`mt-0.5 ${
            isToday ? "text-xs text-blue-800/70 dark:text-blue-200/70" : "text-xs text-neutral-500"
          }`}
        >
          {description}
        </p>
      </div>
      {count === 0 ? (
        emptyMessage ? (
          <p className={`text-sm ${isToday ? "text-blue-800/60 dark:text-blue-200/60" : "text-neutral-500"}`}>
            {emptyMessage}
          </p>
        ) : null
      ) : (
        <div className={`space-y-3 ${isToday ? "" : "pl-0.5"}`}>{children}</div>
      )}
    </section>
  );
}
