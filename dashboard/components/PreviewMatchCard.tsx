"use client";

import { useState } from "react";
import type { FixtureWatchlist, UpcomingFixture, WatchPlayer } from "@/lib/data";
import { formatKickoff, pct } from "@/lib/format";
import {
  bodyEmphasisClass,
  emphasisBadge,
  kickoffEmphasisClass,
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

function topWatchPlayer(watchlist: FixtureWatchlist | null): WatchPlayer | null {
  const all = [...(watchlist?.homeWatch ?? []), ...(watchlist?.awayWatch ?? [])];
  if (all.length === 0) return null;
  return all.reduce((best, p) => (p.pShotsGt05 > best.pShotsGt05 ? p : best), all[0]);
}

export default function PreviewMatchCard({
  fixture,
  watchlist = null,
  index,
  emphasis = "preview",
  pendingLabel = "Analysis available once lineups are confirmed (~20-40min pre-kickoff).",
}: {
  fixture: UpcomingFixture;
  watchlist?: FixtureWatchlist | null;
  index: number;
  emphasis?: TimelineEmphasis;
  pendingLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const hasPlayers =
    (watchlist?.homeWatch.length ?? 0) > 0 || (watchlist?.awayWatch.length ?? 0) > 0;
  const badge = emphasisBadge(emphasis);
  const topPlayer = topWatchPlayer(watchlist);
  const expandable = emphasis === "today";

  const summaryText = hasPlayers && topPlayer
    ? `Pre-lineup watch: ${topPlayer.player} leads at ${pct(topPlayer.pShotsGt05)} shots 1+. Tap for full watchlist.`
    : pendingLabel;

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
              className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-800"
              onClick={(e) => e.stopPropagation()}
            >
              {!hasPlayers ? (
                <p className="text-xs text-neutral-400">
                  Watchlist not available yet. Full goals O/U analysis lands once lineups are
                  confirmed (~20–40 min pre-kickoff).
                </p>
              ) : (
                <>
                  <div className="text-neutral-500 text-xs mb-2">Pre-lineup watchlist</div>
                  <div className="grid grid-cols-2 gap-3">
                    <WatchColumn team={fixture.home} players={watchlist?.homeWatch ?? []} />
                    <WatchColumn team={fixture.away} players={watchlist?.awayWatch ?? []} />
                  </div>
                  <p className="text-[11px] text-neutral-400 mt-3">
                    Recent starters ranked by P(shots 1+) vs this opponent. Confirmed XI and full
                    team/lineup goals model appear ~20–40 min pre-kickoff.
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
