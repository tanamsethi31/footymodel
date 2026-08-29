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
        className="text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors duration-150"
      >
        {open ? "Hide" : "Show"} {count} past prediction{count === 1 ? "" : "s"}
      </button>
      {open && <div className="mt-3 space-y-3">{children}</div>}
    </div>
  );
}
