"use client";

import { useState } from "react";
import type { FixtureWatchlist, UpcomingFixture, WatchPlayer } from "@/lib/data";
import { formatKickoff, pct } from "@/lib/format";
import { emphasisBadge, previewCardEmphasisClass, type TimelineEmphasis } from "@/lib/timelineStyles";

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

function WatchColumn({ team, players }: { team: string; players: WatchPlayer[] }) {
  return (
    <div>
      <div className="text-neutral-500 text-xs mb-1">{team}</div>
      {players.length === 0 ? (
        <p className="text-xs text-neutral-400">No recent starters ranked yet.</p>
      ) : (
        <ul className="space-y-1">
          {players.map((p) => (
            <li key={p.player} className="flex items-baseline justify-between gap-2 text-xs">
              <span className="text-neutral-700 dark:text-neutral-300 truncate">{p.player}</span>
              <span className="font-mono shrink-0 text-neutral-500">{pct(p.pShotsGt05)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function PropsPreviewCard({
  fixture,
  watchlist,
  index,
  emphasis = "preview",
}: {
  fixture: UpcomingFixture;
  watchlist: FixtureWatchlist | null;
  index: number;
  emphasis?: TimelineEmphasis;
}) {
  const [open, setOpen] = useState(false);
  const hasPlayers =
    (watchlist?.homeWatch.length ?? 0) > 0 || (watchlist?.awayWatch.length ?? 0) > 0;
  const badge = emphasisBadge(emphasis);

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
      className={`animate-stagger-in rounded-xl border p-4 transition-transform duration-150 hover:-translate-y-0.5 cursor-pointer ${previewCardEmphasisClass(emphasis)}`}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className={`font-medium flex items-center gap-2 ${emphasis === "today" ? "text-blue-950 dark:text-blue-50" : ""}`}>
          <Chevron open={open} />
          {fixture.home} v {fixture.away}
          <span className={badge.className}>{badge.label}</span>
        </span>
        <span className={`text-xs ${emphasis === "today" ? "text-blue-700/80 dark:text-blue-300/80 font-medium" : "text-neutral-500"}`}>
          {formatKickoff(fixture.kickoff)}
        </span>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <p className={`text-xs ${emphasis === "today" ? "text-blue-800/70 dark:text-blue-200/70" : "text-neutral-400"}`}>
          {hasPlayers
            ? "Tap for key players to watch. Full prop lines after lineups are confirmed."
            : "Player-prop lines available once lineups are confirmed (~20-40min pre-kickoff)."}
        </p>
      </div>

      <div
        className="grid transition-[grid-template-rows] duration-300 ease-in-out"
        style={{ gridTemplateRows: open ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <div
            className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-800"
            onClick={(e) => e.stopPropagation()}
          >
            {!hasPlayers ? (
              <p className="text-xs text-neutral-400">
                Watchlist not available for this fixture yet.
              </p>
            ) : (
              <>
                <div className="text-neutral-500 text-xs mb-2">Key players to watch</div>
                <div className="grid grid-cols-2 gap-3">
                  <WatchColumn team={fixture.home} players={watchlist?.homeWatch ?? []} />
                  <WatchColumn team={fixture.away} players={watchlist?.awayWatch ?? []} />
                </div>
                <p className="text-[11px] text-neutral-400 mt-3">
                  Recent starters ranked by P(shots 1+) vs this opponent, 85 assumed
                  minutes. Not the confirmed XI — those lines land ~20–40 min
                  pre-kickoff.
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
