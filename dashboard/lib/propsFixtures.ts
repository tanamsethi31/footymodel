import type { PropsPick, UpcomingFixture } from "./data";
import { matchKey } from "./upcoming";

export type LoggedFixture = Pick<
  UpcomingFixture,
  "fixtureId" | "home" | "away" | "kickoff"
>;

/** One row per fixture derived from player-prop CSV rows + upcoming calendar. */
export function buildLoggedFixturesFromProps(
  props: PropsPick[],
  upcoming: UpcomingFixture[]
): LoggedFixture[] {
  const byFixture = new Map<string, PropsPick[]>();
  for (const row of props) {
    const arr = byFixture.get(row.fixtureId) ?? [];
    arr.push(row);
    byFixture.set(row.fixtureId, arr);
  }

  const upcomingById = new Map(upcoming.map((f) => [f.fixtureId, f]));
  const upcomingByKey = new Map(
    upcoming.map((f) => [matchKey(f.home, f.away, f.kickoff), f])
  );

  const out: LoggedFixture[] = [];
  for (const [fixtureId, rows] of byFixture) {
    const sample = rows[0];
    const fromCsv =
      sample.home && sample.away
        ? { home: sample.home, away: sample.away, kickoff: sample.kickoff }
        : null;
    const cal =
      upcomingById.get(fixtureId) ??
      (fromCsv
        ? upcomingByKey.get(matchKey(fromCsv.home, fromCsv.away, fromCsv.kickoff))
        : undefined);
    if (!fromCsv && !cal) continue;
    out.push({
      fixtureId,
      home: cal?.home ?? fromCsv!.home,
      away: cal?.away ?? fromCsv!.away,
      kickoff: cal?.kickoff ?? fromCsv!.kickoff,
    });
  }
  return out;
}
