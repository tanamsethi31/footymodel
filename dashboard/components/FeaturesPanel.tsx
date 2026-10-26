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
        note: "Irish-time kickoff windows with live-state badge.",
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
        name: "SofaScore player-prop odds + EV",
        status: "partial",
        note: "Parsed when SofaScore exposes shots/SOT markets; else model-confidence paper stakes.",
      },
      {
        name: "€100 internal paper bankroll (shared)",
        status: "live",
        note: "Player props + goals O/U 2.5 on one ledger; Kelly when odds exist.",
      },
      {
        name: "Match goals Over/Under 2.5 (lineup-aware)",
        status: "live",
        note: "SofaScore match O/U odds + LineupModel; Goals O/U tab + paper bets.",
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
        status: "live",
        note: "Understat rosters + shot logs via scripts/backfill_recent_props.py; proxy XI when rosters lag.",
      },
      {
        name: "CLV / yield vs closing prop lines",
        status: "planned",
        note: "Needs reliable SofaScore closing player-prop capture.",
      },
    ],
  },
  {
    area: "Notifications & app",
    items: [
      {
        name: "Web Push (VAPID)",
        status: "live",
        note: "Fires when the self-hosted props workflow commits new rows.",
      },
      {
        name: "Props-focused notify body",
        status: "live",
        note: "Highlights fixture + top player line when new props land.",
      },
      {
        name: "Self-hosted SofaScore matchday poll",
        status: "live",
        note: "Goals O/U then player props in one Playwright session — docs/MATCHDAY_AUTOMATION.md.",
      },
      {
        name: "Post-match props grading (Understat)",
        status: "live",
        note: "grade_props.yml twice daily + backfill_recent_props.py.",
      },
      {
        name: "Post-match goals O/U grading + bankroll settle",
        status: "live",
        note: "grade_results.yml from matches.parquet + settle_paper_props.py.",
      },
      {
        name: "Cloud calendar / watchlist poll",
        status: "live",
        note: "GitHub-hosted job updates preview without Playwright.",
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
    area: "Research / legacy (not live)",
    items: [
      {
        name: "football-data.co.uk goals recommender CLI",
        status: "planned",
        note: "Historical closing-line backtest only — no edge in RESULTS.md.",
      },
      {
        name: "Goals Kelly staking sim tab",
        status: "planned",
        note: "Historical paper_trades.csv demos; not the SofaScore live ledger.",
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
          What the SofaScore paper-trading app ships today vs what is still on the roadmap.
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
