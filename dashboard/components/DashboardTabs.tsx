"use client";

import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

const TABS = ["Predictions", "Goals O/U", "Track record", "Features", "Glossary"];

export default function DashboardTabs({
  predictions,
  goalsOu,
  trackRecord,
  features,
  glossary,
}: {
  predictions: ReactNode;
  goalsOu: ReactNode;
  trackRecord: ReactNode;
  features: ReactNode;
  glossary: ReactNode;
}) {
  const [active, setActive] = useState(0);
  const panels = [predictions, goalsOu, trackRecord, features, glossary];

  const containerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const didMountRef = useRef(false);
  const [clip, setClip] = useState<{ left: number; right: number } | null>(null);

  useLayoutEffect(() => {
    const wrapper = wrapperRef.current;
    const btn = buttonRefs.current[active];
    if (!wrapper || !btn) return;
    const wrapperRect = wrapper.getBoundingClientRect();
    const btnRect = btn.getBoundingClientRect();
    setClip({
      left: btnRect.left - wrapperRect.left,
      right: wrapperRect.right - btnRect.right,
    });
    if (didMountRef.current) {
      btn.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
    didMountRef.current = true;
  }, [active]);

  return (
    <div>
      <div
        ref={containerRef}
        className="relative inline-flex max-w-full overflow-x-auto bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-full p-1 mb-8"
      >
        <div ref={wrapperRef} className="relative flex shrink-0">
          {TABS.map((t, i) => (
            <button
              key={t}
              ref={(el) => {
                buttonRefs.current[i] = el;
              }}
              onClick={() => setActive(i)}
              className="relative z-10 w-24 sm:w-28 shrink-0 px-2 py-1.5 rounded-full text-sm font-medium text-neutral-500 dark:text-neutral-400 whitespace-nowrap text-center active:scale-[0.97] transition-transform duration-150"
            >
              {t}
            </button>
          ))}
          {clip && (
            <div
              className="absolute inset-y-0 left-0 flex pointer-events-none bg-blue-600 rounded-full transition-[clip-path] duration-[260ms] [transition-timing-function:cubic-bezier(0.23,1,0.32,1)]"
              style={{
                clipPath: `inset(0 ${clip.right}px 0 ${clip.left}px round 999px)`,
              }}
            >
              {TABS.map((t) => (
                <span
                  key={t}
                  className="w-24 sm:w-28 shrink-0 px-2 py-1.5 rounded-full text-sm font-medium text-white whitespace-nowrap text-center"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
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
