"use client";

import { useState, type ReactNode } from "react";

export default function PastDisclosure({
  count,
  children,
}: {
  count: number;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  if (count === 0) return null;

  return (
    <div className="mt-4">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-medium transition-colors duration-150 active:scale-[0.97] ${
          open
            ? "bg-blue-600 border-blue-600 text-white"
            : "bg-neutral-100 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-neutral-300 dark:hover:border-neutral-700"
        }`}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          className={`w-4 h-4 shrink-0 transition-transform duration-200 ${
            open ? "rotate-90 text-white" : "text-blue-600 dark:text-blue-400"
          }`}
          aria-hidden="true"
        >
          <path
            d="M9 6l6 6-6 6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {open ? "Hide" : "Show"} {count} past prediction{count === 1 ? "" : "s"}
      </button>
      <div
        className="grid transition-[grid-template-rows] duration-300 ease-in-out"
        style={{ gridTemplateRows: open ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <div className="mt-3 space-y-3">{children}</div>
        </div>
      </div>
    </div>
  );
}
