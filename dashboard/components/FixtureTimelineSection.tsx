import type { ReactNode } from "react";

export default function FixtureTimelineSection({
  title,
  description,
  emptyMessage,
  count,
  children,
}: {
  title: string;
  description: string;
  emptyMessage?: string;
  count: number;
  children: ReactNode;
}) {
  return (
    <div className="mb-8 last:mb-0">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{title}</h3>
        <p className="text-xs text-neutral-500 mt-0.5">{description}</p>
      </div>
      {count === 0 ? (
        emptyMessage ? (
          <p className="text-sm text-neutral-500">{emptyMessage}</p>
        ) : null
      ) : (
        <div className="space-y-3">{children}</div>
      )}
    </div>
  );
}
