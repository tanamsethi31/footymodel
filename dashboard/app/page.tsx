import { getGoalsPicks, getPropsPicks } from "@/lib/data";
import SubscribeButton from "@/components/SubscribeButton";

export const revalidate = 60;

function formatKickoff(iso: string) {
  try {
    return new Date(iso).toLocaleString("en-GB", {
      weekday: "short",
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function pct(n: number | null) {
  return n === null ? "—" : `${(n * 100).toFixed(1)}%`;
}

function odds(n: number | null) {
  return n === null ? "—" : n.toFixed(2);
}

function EvBadge({ ev }: { ev: number | null }) {
  if (ev === null) return <span className="text-neutral-400">—</span>;
  const positive = ev > 0;
  return (
    <span
      className={`font-mono font-medium ${
        positive
          ? "text-emerald-600 dark:text-emerald-400"
          : "text-red-500 dark:text-red-400"
      }`}
    >
      {positive ? "+" : ""}
      {(ev * 100).toFixed(1)}%
    </span>
  );
}

const SOURCE_LABEL: Record<string, string> = {
  "api-football": "API-Football",
  sofascore: "SofaScore",
  rapidapi: "RapidAPI",
};

export default async function Home() {
  const [goals, props] = await Promise.all([getGoalsPicks(), getPropsPicks()]);

  // Group props rows by fixture so each match renders as one card.
  const propsByFixture = new Map<string, typeof props>();
  for (const p of props) {
    const arr = propsByFixture.get(p.fixtureId) ?? [];
    arr.push(p);
    propsByFixture.set(p.fixtureId, arr);
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 sm:py-14">
      <header className="flex items-start justify-between gap-4 mb-10">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">footymodel</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Live predictions — Premier League goals O/U 2.5 and player shots
            / shots-on-target, both backtested. Paper-trade only, nothing
            here is a real bet.
          </p>
        </div>
        <SubscribeButton />
      </header>

      <section className="mb-14">
        <h2 className="text-lg font-semibold mb-1">Goals — Over/Under 2.5</h2>
        <p className="text-sm text-neutral-500 mb-5">
          Confirmed-lineup model, pooled t=3.04 backtested (individually
          significant on the Premier League alone, t=2.23).
        </p>
        {goals.length === 0 ? (
          <p className="text-sm text-neutral-500">
            No predictions logged yet — check back once a fixture&apos;s
            lineup is confirmed pre-kickoff.
          </p>
        ) : (
          <div className="space-y-3">
            {goals.map((g) => (
              <div
                key={g.fixtureId}
                className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4"
              >
                <div className="flex items-baseline justify-between gap-2 flex-wrap">
                  <span className="font-medium">
                    {g.home} v {g.away}
                  </span>
                  <span className="text-xs text-neutral-500">
                    {formatKickoff(g.kickoff)}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  <div>
                    <div className="text-neutral-500 text-xs">Model P(O2.5)</div>
                    <div className="font-mono">{pct(g.modelPOver25)}</div>
                  </div>
                  <div>
                    <div className="text-neutral-500 text-xs">xG total</div>
                    <div className="font-mono">{g.expTotalGoals.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-neutral-500 text-xs">Odds O / U</div>
                    <div className="font-mono">
                      {odds(g.oddsOver25)} / {odds(g.oddsUnder25)}
                    </div>
                  </div>
                  <div>
                    <div className="text-neutral-500 text-xs">EV Over / Under</div>
                    <div className="flex gap-2">
                      <EvBadge ev={g.evOver25} />
                      <EvBadge ev={g.evUnder25} />
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2 text-xs text-neutral-400">
                  <span>
                    starters matched {g.nHomeMatched}/{g.nAwayMatched}
                  </span>
                  <span>·</span>
                  <span>{SOURCE_LABEL[g.source ?? ""] ?? g.source}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-1">
          Player shots &amp; shots-on-target
        </h2>
        <p className="text-sm text-neutral-500 mb-5">
          Well-calibrated in backtesting (gaps within ±0.03). Live profit
          untested — no historical prop-odds archive exists to backtest
          against.
        </p>
        {propsByFixture.size === 0 ? (
          <p className="text-sm text-neutral-500">
            No prop predictions logged yet.
          </p>
        ) : (
          <div className="space-y-6">
            {[...propsByFixture.entries()].map(([fixtureId, rows]) => (
              <div
                key={fixtureId}
                className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4"
              >
                <div className="flex items-baseline justify-between gap-2 flex-wrap mb-3">
                  <span className="font-medium">
                    {[...new Set(rows.map((r) => r.team))].join(" v ")}
                  </span>
                  <span className="text-xs text-neutral-500">
                    {formatKickoff(rows[0].kickoff)}
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-neutral-500 border-b border-neutral-200 dark:border-neutral-800">
                        <th className="py-1.5 pr-3 font-normal">Player</th>
                        <th className="py-1.5 pr-3 font-normal">Shots 1+</th>
                        <th className="py-1.5 pr-3 font-normal">SOT 1+</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => (
                        <tr
                          key={`${r.fixtureId}-${r.player}`}
                          className="border-b border-neutral-100 dark:border-neutral-900 last:border-0"
                        >
                          <td className="py-1.5 pr-3">{r.player}</td>
                          <td className="py-1.5 pr-3 font-mono">
                            {pct(r.pShotsGt05)}
                            {r.oddsShotsGt05 !== null && (
                              <span className="text-neutral-400">
                                {" "}
                                @ {odds(r.oddsShotsGt05)}
                              </span>
                            )}
                          </td>
                          <td className="py-1.5 pr-3 font-mono">
                            {pct(r.pSotGt05)}
                            {r.oddsSotGt05 !== null && (
                              <span className="text-neutral-400">
                                {" "}
                                @ {odds(r.oddsSotGt05)}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <footer className="mt-16 text-xs text-neutral-400">
        Research project — paper-trade only, no real money involved.
        Refreshes automatically as new predictions are logged.
      </footer>
    </div>
  );
}
