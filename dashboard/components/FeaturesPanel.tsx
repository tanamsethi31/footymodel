const FEATURES: {
  area: string;
  items: { name: string; status: "live" | "partial" | "planned"; note: string }[];
}[] = [
  {
    area: "Pre-match & upcoming",
    items: [
      {
        name: "10-day fixture calendar",
        status: "live",
        note: "PL kickoffs from FPL + Understat fallback.",
      },
      {
        name: "Today / Upcoming / Past buckets",
        status: "live",
        note: "UTC kickoff windows with live-state badge.",
      },
      {
        name: "Players to watch (pre-lineup)",
        status: "live",
        note: "Ranked by P(shots 1+) vs opponent; not the confirmed XI.",
      },
      {
        name: "Expandable pre-match cards",
        status: "live",
        note: "Tap for watchlist copy and assumed 85-minute model context.",
      },
    ],
  },
  {
    area: "Confirmed lineups & analysis",
    items: [
      {
        name: "Confirmed starting XI display",
        status: "live",
        note: "Logged with each props poll when lineups are available.",
      },
      {
        name: "Per-player shots & SOT probabilities",
        status: "live",
        note: "1+/2+/3+ shots and 1+/2+ SOT thresholds.",
      },
      {
        name: "Full market grid (odds when fetched)",
        status: "partial",
        note: "EV shown when API-Football returns player line markets.",
      },
      {
        name: "Most probable strip",
        status: "live",
        note: "Top model probabilities across upcoming fixtures.",
      },
      {
        name: "Team toggle + threshold pills",
        status: "live",
        note: "Quick scan table on today’s matches.",
      },
    ],
  },
  {
    area: "Past matches",
    items: [
      {
        name: "Past predictions disclosure",
        status: "live",
        note: "Collapsed list of finished fixtures with logged lines.",
      },
      {
        name: "Result vs actual shots/SOT grading",
        status: "planned",
        note: "Needs post-match WhoScored/FBref ingest + graded_props.csv.",
      },
      {
        name: "CLV / yield on prop bets",
        status: "planned",
        note: "Depends on grading + closing prop odds capture.",
      },
    ],
  },
  {
    area: "Notifications & app",
    items: [
      {
        name: "Web Push (VAPID)",
        status: "live",
        note: "Subscribe on this device; fires when live_poll commits new rows.",
      },
      {
        name: "Props-focused notify body",
        status: "live",
        note: "Highlights fixture + top player line when new props land.",
      },
      {
        name: "PWA manifest / install",
        status: "partial",
        note: "manifest.json present; add icons for home-screen install.",
      },
      {
        name: "Deep link to fixture",
        status: "planned",
        note: "Notify URL could open #fixture-{id} on the Predictions tab.",
      },
    ],
  },
  {
    area: "Retired (goals O/U)",
    items: [
      {
        name: "Match goals Over/Under 2.5 tab",
        status: "planned",
        note: "Removed from dashboard; code kept in repo for reference only.",
      },
      {
        name: "Goals Kelly staking sim tab",
        status: "planned",
        note: "Hidden; was tied to goals paper-trade history.",
      },
    ],
  },
];

const STATUS_STYLES = {
  live: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  partial: "bg-amber-500/15 text-amber-800 dark:text-amber-300",
  planned: "bg-neutral-200/80 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400",
};

export default function FeaturesPanel() {
  return (
    <section className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold mb-1">Features checklist</h2>
        <p className="text-sm text-neutral-500">
          What the props-focused app ships today vs what is still on the roadmap.
          Use this to sanity-check releases before matchday.
        </p>
      </div>
      {FEATURES.map((group) => (
        <div key={group.area}>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500 mb-3">
            {group.area}
          </h3>
          <ul className="space-y-3">
            {group.items.map((item) => (
              <li
                key={item.name}
                className="rounded-lg border border-neutral-200 dark:border-neutral-800 px-4 py-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="font-medium">{item.name}</span>
                  <span
                    className={`text-[10px] uppercase tracking-wide font-semibold px-2 py-0.5 rounded-full ${STATUS_STYLES[item.status]}`}
                  >
                    {item.status}
                  </span>
                </div>
                <p className="text-neutral-500 text-xs">{item.note}</p>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
