"use client";

import { useState } from "react";
import type { GoalsPick, MatchDetail } from "@/lib/data";
import { formatKickoff, pct, odds, EvBadge, SOURCE_LABEL } from "@/lib/format";

const CONFIDENCE_THRESHOLD = 0.05;

function confidenceLine(detail: MatchDetail): string {
  const gap = Math.abs(detail.pOver25Team - detail.pOver25Full);
  return gap < CONFIDENCE_THRESHOLD
    ? "Team and lineup models agree closely."
    : "Team and lineup models diverge.";
}

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

export default function MatchCard({
  match,
  detail,
  index,
}: {
  match: GoalsPick;
  detail: MatchDetail | null;
  index: number;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={open}
      onClick={() => setOpen((o) => !o)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setOpen((o) => !o);
        }
      }}
      className="animate-stagger-in rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 transition-transform duration-150 hover:-translate-y-0.5 cursor-pointer"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className="font-medium flex items-center gap-2">
          <Chevron open={open} />
          {match.home} v {match.away}
        </span>
        <span className="text-xs text-neutral-500">{formatKickoff(match.kickoff)}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div>
          <div className="text-neutral-500 text-xs">Model P(O2.5)</div>
          <div className="font-mono">{pct(match.modelPOver25)}</div>
        </div>
        <div>
          <div className="text-neutral-500 text-xs">xG total</div>
          <div className="font-mono">{match.expTotalGoals.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-neutral-500 text-xs">Odds O / U</div>
          <div className="font-mono">
            {odds(match.oddsOver25)} / {odds(match.oddsUnder25)}
          </div>
        </div>
        <div>
          <div className="text-neutral-500 text-xs">EV Over / Under</div>
          <div className="flex gap-2">
            <EvBadge ev={match.evOver25} />
            <EvBadge ev={match.evUnder25} />
          </div>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs text-neutral-400">
        <span>
          starters matched {match.nHomeMatched}/{match.nAwayMatched}
        </span>
        <span>·</span>
        <span>{SOURCE_LABEL[match.source ?? ""] ?? match.source}</span>
      </div>

      <div
        className="grid transition-[grid-template-rows] duration-300 ease-in-out"
        style={{ gridTemplateRows: open ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <div
            className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-800 text-sm"
            onClick={(e) => e.stopPropagation()}
          >
            {detail === null ? (
              <p className="text-xs text-neutral-400">
                Detailed breakdown not available for this prediction.
              </p>
            ) : (
              <>
                <div className="text-neutral-500 text-xs mb-2">Model breakdown</div>
                <div className="grid grid-cols-3 gap-3 font-mono text-xs mb-3">
                  <div>
                    <div className="text-neutral-400">Team model</div>
                    <div>
                      {detail.expTeam.toFixed(2)} xG · {pct(detail.pOver25Team)}
                    </div>
                  </div>
                  <div>
                    <div className="text-neutral-400">Lineup model</div>
                    <div>
                      {detail.expFull.toFixed(2)} xG · {pct(detail.pOver25Full)}
                    </div>
                  </div>
                  <div>
                    <div className="text-neutral-400">Blended</div>
                    <div>
                      {match.expTotalGoals.toFixed(2)} xG · {pct(match.modelPOver25)}
                    </div>
                  </div>
                </div>
                <p className="text-xs text-neutral-500 mb-3">{confidenceLine(detail)}</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-neutral-500 text-xs mb-1">{match.home}</div>
                    <ul className="text-xs text-neutral-600 dark:text-neutral-400 space-y-0.5">
                      {detail.homeStarters.map((n) => (
                        <li key={n}>{n}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className="text-neutral-500 text-xs mb-1">{match.away}</div>
                    <ul className="text-xs text-neutral-600 dark:text-neutral-400 space-y-0.5">
                      {detail.awayStarters.map((n) => (
                        <li key={n}>{n}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
