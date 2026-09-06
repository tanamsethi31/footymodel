"use client";

import { useState } from "react";
import type { UpcomingFixture } from "@/lib/data";
import { formatKickoff } from "@/lib/format";
import {
  bodyEmphasisClass,
  emphasisBadge,
  kickoffEmphasisClass,
  liveBadge,
  previewCardEmphasisClass,
  titleEmphasisClass,
  type TimelineEmphasis,
} from "@/lib/timelineStyles";

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className={`w-4 h-4 shrink-0 text-neutral-400 transition-transform duration-150 ${
        open ? "rotate-180" : ""
      }`}
      aria-hidden="true"
    >
      <path
        d="M6 9l6 6 6-6"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Pre-lineup placeholder for the Goals O/U tab — no player props content. */
export default function PreviewMatchCard({
  fixture,
  index,
  emphasis = "preview",
  live = false,
}: {
  fixture: UpcomingFixture;
  index: number;
  emphasis?: TimelineEmphasis;
  live?: boolean;
}) {
  const expandable = emphasis === "today";
  const [open, setOpen] = useState(expandable && live);
  const badge = emphasisBadge(emphasis);
  const livePill = liveBadge();

  const summaryText = live
    ? "Match in progress — goals O/U 2.5 analysis lands once confirmed lineups are logged."
    : "Goals O/U 2.5 analysis available once lineups are confirmed (~20–40 min pre-kickoff).";

  return (
    <div
      role={expandable ? "button" : undefined}
      tabIndex={expandable ? 0 : undefined}
      aria-expanded={expandable ? open : undefined}
      onClick={expandable ? () => setOpen((o) => !o) : undefined}
      onKeyDown={
        expandable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setOpen((o) => !o);
              }
            }
          : undefined
      }
      className={`animate-stagger-in rounded-xl border p-4 ${
        expandable
          ? "transition-transform duration-150 hover:-translate-y-0.5 cursor-pointer"
          : ""
      } ${previewCardEmphasisClass(emphasis)}`}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className={`font-medium flex items-center gap-2 flex-wrap ${titleEmphasisClass(emphasis)}`}>
          {expandable && <Chevron open={open} />}
          {fixture.home} v {fixture.away}
          <span className={badge.className}>{badge.label}</span>
          {live && <span className={livePill.className}>{livePill.label}</span>}
        </span>
        <span className={`text-xs ${kickoffEmphasisClass(emphasis)}`}>
          {formatKickoff(fixture.kickoff)}
        </span>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <p className={`text-xs ${bodyEmphasisClass(emphasis)}`}>{summaryText}</p>
      </div>

      {expandable && (
        <div
          className="grid transition-[grid-template-rows] duration-300 ease-in-out"
          style={{ gridTemplateRows: open ? "1fr" : "0fr" }}
        >
          <div className="overflow-hidden">
            <div
              className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-800 text-xs text-neutral-500 space-y-2"
              onClick={(e) => e.stopPropagation()}
            >
              <p>
                Once lineups are confirmed (~20–40 min pre-kickoff), this card fills in with
                match-level goals output:
              </p>
              <ul className="list-disc pl-4 space-y-1 text-neutral-400">
                <li>Model P(Over 2.5) and expected total goals (xG)</li>
                <li>Market O/U 2.5 odds and fair probability</li>
                <li>Expected value on Over and Under</li>
                <li>Team vs lineup model breakdown and confirmed XIs</li>
              </ul>
              <p className="text-neutral-400">
                Player shots and SOT lines live on the Player props tab.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
