export type TimelineEmphasis = "today" | "preview";

export function cardEmphasisClass(emphasis: TimelineEmphasis = "preview"): string {
  if (emphasis === "today") {
    return "border-blue-300 dark:border-blue-700 bg-white dark:bg-neutral-900 shadow-sm ring-1 ring-blue-100 dark:ring-blue-900/40";
  }
  return "border-neutral-200 dark:border-neutral-800";
}

export function previewCardEmphasisClass(emphasis: TimelineEmphasis = "preview"): string {
  if (emphasis === "today") {
    return "border-blue-300 dark:border-blue-700 bg-blue-50/40 dark:bg-blue-950/25 ring-1 ring-blue-100 dark:ring-blue-900/30";
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
        "text-[10px] uppercase tracking-wide font-semibold text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-full px-2 py-0.5",
    };
  }
  return {
    label: "Preview",
    className:
      "text-[10px] uppercase tracking-wide font-medium text-neutral-500 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700 rounded-full px-2 py-0.5",
  };
}
