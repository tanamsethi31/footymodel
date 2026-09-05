"use client";

import { useState } from "react";
import type { PropsPick } from "@/lib/data";
import { formatKickoff, probClass } from "@/lib/format";
import { cardEmphasisClass, emphasisBadge, type TimelineEmphasis } from "@/lib/timelineStyles";

const THRESHOLDS = ["1+", "2+", "3+"];

function valueAt(row: PropsPick, stat: "shots" | "sot", idx: number): number | null {
  if (stat === "shots") return [row.pShotsGt05, row.pShotsGt15, row.pShotsGt25][idx];
  return [row.pSotGt05, row.pSotGt15, null][idx]; // no SOT 3+ data exists yet
}

export default function MatchPropsTable({
  fixtureId,
  rows,
  emphasis = "preview",
}: {
  fixtureId: string;
  rows: PropsPick[];
  emphasis?: TimelineEmphasis;
}) {
  const teams = [...new Set(rows.map((r) => r.team))];
  const [activeTeam, setActiveTeam] = useState(0);
  const [thresh, setThresh] = useState(0);
  const [swapping, setSwapping] = useState(false);

  function pick(i: number) {
    if (i === thresh) return;
    setSwapping(true);
    setTimeout(() => {
      setThresh(i);
      setSwapping(false);
    }, 90);
  }

  const teamRows = rows.filter((r) => r.team === teams[activeTeam]);
  const badge = emphasisBadge(emphasis);

  return (
    <div className={`rounded-xl border p-4 ${cardEmphasisClass(emphasis)}`}>
      <div className="flex items-baseline justify-between gap-2 flex-wrap mb-3">
        <span className="font-medium flex items-center gap-2 flex-wrap">
          {teams.join(" v ")}
          <span className={badge.className}>{badge.label}</span>
        </span>
        <span className={`text-xs ${emphasis === "today" ? "text-blue-700/80 dark:text-blue-300/80 font-medium" : "text-neutral-500"}`}>
          {formatKickoff(rows[0].kickoff)}
        </span>
      </div>

      <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
        <div className="inline-flex bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg p-0.5 gap-0.5">
          {teams.map((t, i) => (
            <button
              key={t}
              onClick={() => setActiveTeam(i)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors duration-150 active:scale-95 ${
                i === activeTeam
                  ? "bg-white dark:bg-neutral-100 text-neutral-900"
                  : "text-neutral-500 dark:text-neutral-400"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="inline-flex bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg p-0.5 gap-0.5">
          {THRESHOLDS.map((t, i) => (
            <button
              key={t}
              onClick={() => pick(i)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors duration-150 active:scale-95 ${
                i === thresh
                  ? "bg-white dark:bg-neutral-100 text-neutral-900"
                  : "text-neutral-500 dark:text-neutral-400"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-neutral-500 border-b border-neutral-200 dark:border-neutral-800">
              <th className="py-1.5 pr-3 font-normal">Player</th>
              <th className="py-1.5 pr-3 font-normal">Shots on Target</th>
              <th className="py-1.5 pr-3 font-normal">Total Shots</th>
            </tr>
          </thead>
          <tbody>
            {teamRows.map((r) => {
              const sot = valueAt(r, "sot", thresh);
              const shots = valueAt(r, "shots", thresh);
              return (
                <tr
                  key={`${fixtureId}-${r.player}`}
                  className="border-b border-neutral-100 dark:border-neutral-900 last:border-0"
                >
                  <td className="py-1.5 pr-3">{r.player}</td>
                  <td
                    className={`py-1.5 pr-3 font-mono transition-[filter,opacity] duration-150 ${probClass(
                      sot
                    )} ${swapping ? "blur-[3px] opacity-50" : ""}`}
                  >
                    {sot === null ? "-" : `${(sot * 100).toFixed(0)}%`}
                  </td>
                  <td
                    className={`py-1.5 pr-3 font-mono transition-[filter,opacity] duration-150 ${probClass(
                      shots
                    )} ${swapping ? "blur-[3px] opacity-50" : ""}`}
                  >
                    {shots === null ? "-" : `${(shots * 100).toFixed(0)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
