"use client";

import { useState } from "react";
import type { GradedPropsPlayer, MatchDetail, PropsPick } from "@/lib/data";
import { formatKickoff, odds, probClass } from "@/lib/format";
import {
  cardEmphasisClass,
  emphasisBadge,
  kickoffEmphasisClass,
  liveBadge,
  type TimelineEmphasis,
} from "@/lib/timelineStyles";

const THRESHOLDS = ["1+", "2+", "3+"];

const MARKETS = [
  { label: "Shots 1+", prob: "pShotsGt05" as const, odds: "oddsShotsGt05" as const },
  { label: "Shots 2+", prob: "pShotsGt15" as const, odds: "oddsShotsGt15" as const },
  { label: "Shots 3+", prob: "pShotsGt25" as const, odds: "oddsShotsGt25" as const },
  { label: "SOT 1+", prob: "pSotGt05" as const, odds: "oddsSotGt05" as const },
  { label: "SOT 2+", prob: "pSotGt15" as const, odds: "oddsSotGt15" as const },
];

function valueAt(row: PropsPick, stat: "shots" | "sot", idx: number): number | null {
  if (stat === "shots") return [row.pShotsGt05, row.pShotsGt15, row.pShotsGt25][idx];
  return [row.pSotGt05, row.pSotGt15, null][idx];
}

function topPlayer(rows: PropsPick[]): PropsPick | null {
  if (rows.length === 0) return null;
  return rows.reduce((best, r) => {
    const p = r.pShotsGt05 ?? 0;
    const bestP = best.pShotsGt05 ?? 0;
    return p > bestP ? r : best;
  }, rows[0]);
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

function PlayerMarketGrid({ rows }: { rows: PropsPick[] }) {
  return (
    <div className="space-y-4">
      {rows.map((r) => (
        <div
          key={r.player}
          className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3"
        >
          <div className="text-sm font-medium mb-2">{r.player}</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-xs">
            {MARKETS.map((m) => {
              const prob = r[m.prob];
              const marketOdds = r[m.odds];
              return (
                <div key={m.label} className="rounded-md bg-neutral-50 dark:bg-neutral-900/60 p-2">
                  <div className="text-neutral-500 mb-1">{m.label}</div>
                  <div className={`font-mono ${probClass(prob)}`}>
                    {prob === null ? "-" : `${(prob * 100).toFixed(0)}%`}
                  </div>
                  {marketOdds !== null && (
                    <div className="text-neutral-400 font-mono mt-0.5">@ {odds(marketOdds)}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function LineupBlock({ lineup, home, away }: { lineup: MatchDetail | null; home: string; away: string }) {
  if (!lineup || (lineup.homeStarters.length === 0 && lineup.awayStarters.length === 0)) {
    return null;
  }
  return (
    <div className="mb-4 rounded-lg border border-neutral-200 dark:border-neutral-800 p-3">
      <div className="text-neutral-500 text-xs mb-2">Confirmed starting XI</div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
        <div>
          <div className="font-medium mb-1">{home}</div>
          <ul className="text-neutral-600 dark:text-neutral-400 space-y-0.5">
            {lineup.homeStarters.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
        <div>
          <div className="font-medium mb-1">{away}</div>
          <ul className="text-neutral-600 dark:text-neutral-400 space-y-0.5">
            {lineup.awayStarters.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function MatchPropsTable({
  fixtureId,
  home,
  away,
  rows,
  lineup = null,
  playerGrades = null,
  emphasis = "preview",
  live = false,
}: {
  fixtureId: string;
  home: string;
  away: string;
  rows: PropsPick[];
  lineup?: MatchDetail | null;
  playerGrades?: Map<string, GradedPropsPlayer> | null;
  emphasis?: TimelineEmphasis;
  live?: boolean;
}) {
  const showActuals = playerGrades && playerGrades.size > 0;
  const teams = home && away ? [home, away] : [...new Set(rows.map((r) => r.team))];
  const [activeTeam, setActiveTeam] = useState(0);
  const [thresh, setThresh] = useState(0);
  const [swapping, setSwapping] = useState(false);
  const [open, setOpen] = useState(emphasis === "today");
  const expandable = emphasis === "today";

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
  const livePill = liveBadge();
  const leader = topPlayer(rows);

  const summary =
    leader && leader.pShotsGt05 !== null
      ? `${rows.length} players · top ${leader.player} ${(leader.pShotsGt05 * 100).toFixed(0)}% shots 1+`
      : `${rows.length} players logged`;

  const cardClass = `${cardEmphasisClass(emphasis)} ${
    expandable ? "transition-transform duration-150 hover:-translate-y-0.5 cursor-pointer" : ""
  }`;

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
      className={`rounded-xl border p-4 ${cardClass}`}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap mb-1">
        <span className="font-medium flex items-center gap-2 flex-wrap">
          {expandable && <Chevron open={open} />}
          {home && away ? `${home} v ${away}` : teams.join(" v ")}
          <span className={badge.className}>{badge.label}</span>
          {live && <span className={livePill.className}>{livePill.label}</span>}
        </span>
        <span className={`text-xs ${kickoffEmphasisClass(emphasis)}`}>
          {formatKickoff(rows[0].kickoff)}
        </span>
      </div>
      {expandable && !open && (
        <p className="text-xs text-neutral-500 mb-2">{summary} · tap for full analysis</p>
      )}

      <div
        className={expandable ? "grid transition-[grid-template-rows] duration-300 ease-in-out" : ""}
        style={expandable ? { gridTemplateRows: open ? "1fr" : "0fr" } : undefined}
        onClick={expandable ? (e) => e.stopPropagation() : undefined}
      >
        <div className={expandable ? "overflow-hidden" : ""}>
          <div className={expandable ? "pt-2" : ""}>
            <LineupBlock lineup={lineup} home={home || teams[0] || ""} away={away || teams[1] || ""} />
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
                    {showActuals && <th className="py-1.5 pr-3 font-normal">Actual</th>}
                  </tr>
                </thead>
                <tbody>
                  {teamRows.map((r) => {
                    const sot = valueAt(r, "sot", thresh);
                    const shots = valueAt(r, "shots", thresh);
                    const grade = playerGrades?.get(r.player);
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
                        {showActuals && (
                          <td className="py-1.5 pr-3 font-mono text-xs text-neutral-500">
                            {grade?.actualShots != null
                              ? `${grade.actualShots} sh${grade.actualSot != null ? ` · ${grade.actualSot} sot` : ""}`
                              : "—"}
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {expandable && (
              <div className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-800">
                <div className="text-neutral-500 text-xs mb-3">
                  Full market breakdown — {teams[activeTeam]}
                </div>
                <PlayerMarketGrid rows={teamRows} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
