"use client";

import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

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

  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const [clip, setClip] = useState<{ left: number; right: number } | null>(null);

  useLayoutEffect(() => {
    const container = containerRef.current;
    const btn = buttonRefs.current[active];
    if (!container || !btn) return;
    const containerRect = container.getBoundingClientRect();
    const btnRect = btn.getBoundingClientRect();
    // The clip-path overlay sits at `inset-1` inside the container, so its own
    // coordinate origin is already shifted in by the container's padding -
    // subtract it out here or every clip would be off by exactly that amount.
    const style = getComputedStyle(container);
    const padLeft = parseFloat(style.paddingLeft) || 0;
    const padRight = parseFloat(style.paddingRight) || 0;
    setClip({
      left: btnRect.left - containerRect.left - padLeft,
      right: containerRect.right - btnRect.right - padRight,
    });
  }, [active]);

  return (
    <div>
      <div
        ref={containerRef}
        className="relative inline-flex bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-full p-1 mb-8"
      >
        <div className="flex">
          {TABS.map((t, i) => (
            <button
              key={t}
              ref={(el) => {
                buttonRefs.current[i] = el;
              }}
              onClick={() => setActive(i)}
              className="relative z-10 w-32 px-2 py-1.5 rounded-full text-sm font-medium text-neutral-500 dark:text-neutral-400 whitespace-nowrap text-center active:scale-[0.97] transition-transform duration-150"
            >
              {t}
            </button>
          ))}
        </div>
        {clip && (
          <div
            className="absolute inset-1 flex pointer-events-none bg-blue-600 dark:bg-blue-500 rounded-full transition-[clip-path] duration-[260ms] [transition-timing-function:cubic-bezier(0.23,1,0.32,1)]"
            style={{
              clipPath: `inset(0 ${clip.right}px 0 ${clip.left}px round 999px)`,
            }}
          >
            {TABS.map((t) => (
              <span
                key={t}
                className="w-32 px-2 py-1.5 rounded-full text-sm font-medium text-white whitespace-nowrap text-center"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {panels.map((panel, i) => (
        <div key={i} hidden={i !== active} className={i === active ? "animate-panel-in" : ""}>
          {panel}
        </div>
      ))}
    </div>
  );
}
