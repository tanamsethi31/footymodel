export type TimelineEmphasis = "today" | "preview";

export function sectionTodayClass(): string {
  return "rounded-2xl border border-neutral-300 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950/80 p-4 sm:p-5 shadow-sm";
}

export function sectionTodayTitleClass(): string {
  return "text-base text-neutral-900 dark:text-neutral-100";
}

export function sectionTodayDescriptionClass(): string {
  return "text-xs text-neutral-600 dark:text-neutral-400";
}

export function sectionTodayEmptyClass(): string {
  return "text-sm text-neutral-500 dark:text-neutral-500";
}

export function sectionTodayBadgeClass(): string {
  return "text-[10px] uppercase tracking-wider font-semibold text-neutral-700 dark:text-neutral-200 bg-neutral-200 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-full px-2.5 py-0.5";
}

export function cardEmphasisClass(emphasis: TimelineEmphasis = "preview"): string {
  if (emphasis === "today") {
    return "border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-sm ring-1 ring-neutral-200 dark:ring-neutral-800";
  }
  return "border-neutral-200 dark:border-neutral-800";
}

export function previewCardEmphasisClass(emphasis: TimelineEmphasis = "preview"): string {
  if (emphasis === "today") {
    return "border-neutral-300 dark:border-neutral-700 bg-neutral-50/80 dark:bg-neutral-900/60 ring-1 ring-neutral-200 dark:ring-neutral-800";
  }
  return "border-dashed border-neutral-300 dark:border-neutral-700";
}

export function emphasisBadge(emphasis: TimelineEmphasis): {
  label: string;
  className: string;
} {
  if (emphasis === "today") {
    return {
      label: "Today",
      className:
        "text-[10px] uppercase tracking-wide font-semibold text-neutral-800 dark:text-neutral-200 bg-neutral-200 dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded-full px-2 py-0.5",
    };
  }
  return {
    label: "Preview",
    className:
      "text-[10px] uppercase tracking-wide font-medium text-neutral-500 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700 rounded-full px-2 py-0.5",
  };
}

export function titleEmphasisClass(emphasis: TimelineEmphasis = "preview"): string {
  return emphasis === "today" ? "text-neutral-950 dark:text-neutral-50" : "";
}

export function kickoffEmphasisClass(emphasis: TimelineEmphasis = "preview"): string {
  return emphasis === "today"
    ? "text-neutral-700 dark:text-neutral-300 font-medium"
    : "text-neutral-500";
}

export function bodyEmphasisClass(emphasis: TimelineEmphasis = "preview"): string {
  return emphasis === "today"
    ? "text-neutral-600 dark:text-neutral-400"
    : "text-neutral-400";
}
