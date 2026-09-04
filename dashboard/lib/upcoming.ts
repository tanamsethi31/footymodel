import type { FixtureWatchlist, GoalsPick, UpcomingFixture } from "./data";

export const UPCOMING_DISPLAY_LIMIT = 5;

export function matchKey(home: string, away: string, kickoff: string): string {
  const day = new Date(kickoff);
  const ymd = Number.isNaN(day.getTime())
    ? kickoff.slice(0, 10)
    : day.toISOString().slice(0, 10);
  return `${home.trim().toLowerCase()}|${away.trim().toLowerCase()}|${ymd}`;
}

/** Next N Premier League fixtures in kickoff order. Calendar/Understat
 * previews are the source of "what's coming"; a logged prediction for the
 * same match (possibly a different fixture id) replaces the placeholder. */
export function selectNextUpcoming(
  calendar: UpcomingFixture[],
  predicted: Pick<GoalsPick, "fixtureId" | "home" | "away" | "kickoff">[],
  limit = UPCOMING_DISPLAY_LIMIT,
  nowMs = Date.now()
): UpcomingFixture[] {
  const byKey = new Map<string, UpcomingFixture>();

  const consider = (f: UpcomingFixture) => {
    const t = new Date(f.kickoff).getTime();
    if (!Number.isFinite(t) || t <= nowMs) return;
    const k = matchKey(f.home, f.away, f.kickoff);
    const existing = byKey.get(k);
    if (!existing) {
      byKey.set(k, f);
      return;
    }
    const existingPlaceholder = String(existing.fixtureId).startsWith("us_");
    const incomingPlaceholder = String(f.fixtureId).startsWith("us_");
    if (existingPlaceholder && !incomingPlaceholder) {
      byKey.set(k, f);
    }
  };

  for (const f of calendar) consider(f);
  for (const p of predicted) {
    consider({
      fixtureId: p.fixtureId,
      home: p.home,
      away: p.away,
      kickoff: p.kickoff,
    });
  }

  return [...byKey.values()]
    .sort(
      (a, b) =>
        new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime() ||
        a.home.localeCompare(b.home)
    )
    .slice(0, limit);
}

export function watchlistForFixture(
  lists: FixtureWatchlist[],
  fixture: UpcomingFixture
): FixtureWatchlist | null {
  const byId = lists.find((w) => w.fixtureId === fixture.fixtureId);
  if (byId) return byId;
  const k = matchKey(fixture.home, fixture.away, fixture.kickoff);
  return lists.find((w) => matchKey(w.home, w.away, w.kickoff) === k) ?? null;
}
