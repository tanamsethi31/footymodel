"use client";

import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

const TABS = ["Track record", "Goals O/U", "Player props", "Staking", "Glossary"];

export default function DashboardTabs({
  trackRecord,
  goals,
  props,
  staking,
  glossary,
}: {
  trackRecord: ReactNode;
  goals: ReactNode;
  props: ReactNode;
  staking: ReactNode;
  glossary: ReactNode;
}) {
  const [active, setActive] = useState(0);
  const panels = [trackRecord, goals, props, staking, glossary];

  const containerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const didMountRef = useRef(false);
  const [clip, setClip] = useState<{ left: number; right: number } | null>(null);

  useLayoutEffect(() => {
    const wrapper = wrapperRef.current;
    const btn = buttonRefs.current[active];
    if (!wrapper || !btn) return;
    // Measure against the buttons wrapper, not the (fixed-frame) scroll
    // container - the wrapper and the clip-path overlay are both scrolled
    // content, so their coordinate origins shift together when the tab bar
    // is scrolled. Measuring against the container instead was off by
    // exactly scrollLeft whenever the bar was scrolled off zero.
    const wrapperRect = wrapper.getBoundingClientRect();
    const btnRect = btn.getBoundingClientRect();
    setClip({
      left: btnRect.left - wrapperRect.left,
      right: wrapperRect.right - btnRect.right,
    });
    // The tab bar itself scrolls horizontally when there isn't room for all
    // 5 tabs (see the container's overflow-x-auto below) - without this,
    // clicking a tab outside the currently-visible scroll window left the
    // container's scroll position unchanged, so the highlight (and the
    // clicked tab's label) could end up entirely off-screen. Only do this
    // after mount, though - this effect also runs once on initial render
    // (active=0), and scrolling then would risk an unwanted page-level
    // vertical scroll on load if the first tab isn't fully in view yet.
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
              className="relative z-10 w-32 shrink-0 px-2 py-1.5 rounded-full text-sm font-medium text-neutral-500 dark:text-neutral-400 whitespace-nowrap text-center active:scale-[0.97] transition-transform duration-150"
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
                  className="w-32 shrink-0 px-2 py-1.5 rounded-full text-sm font-medium text-white whitespace-nowrap text-center"
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
