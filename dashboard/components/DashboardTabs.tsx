"use client";

import { useState, type ReactNode } from "react";

const TABS = ["Track record", "Goals O/U", "Player props", "Staking"];

export default function DashboardTabs({
  trackRecord,
  goals,
  props,
  staking,
}: {
  trackRecord: ReactNode;
  goals: ReactNode;
  props: ReactNode;
  staking: ReactNode;
}) {
  const [active, setActive] = useState(0);
  const panels = [trackRecord, goals, props, staking];

  return (
    <div>
      <div className="relative inline-flex bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-full p-1 mb-8">
        <div className="flex">
          {TABS.map((t, i) => (
            <button
              key={t}
              onClick={() => setActive(i)}
              className="relative z-10 px-4 py-1.5 rounded-full text-sm font-medium text-neutral-500 dark:text-neutral-400 whitespace-nowrap active:scale-[0.97] transition-transform duration-150"
            >
              {t}
            </button>
          ))}
        </div>
        <div
          className="absolute inset-1 flex pointer-events-none bg-white dark:bg-neutral-100 rounded-full transition-[clip-path] duration-[260ms] [transition-timing-function:cubic-bezier(0.23,1,0.32,1)]"
          style={{
            clipPath: `inset(0 ${100 - ((active + 1) / TABS.length) * 100}% 0 ${
              (active / TABS.length) * 100
            }% round 999px)`,
          }}
        >
          {TABS.map((t) => (
            <span
              key={t}
              className="px-4 py-1.5 rounded-full text-sm font-medium text-neutral-900 whitespace-nowrap"
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      {panels.map((panel, i) => (
        <div key={i} hidden={i !== active} className={i === active ? "animate-panel-in" : ""}>
          {panel}
        </div>
      ))}
    </div>
  );
}
