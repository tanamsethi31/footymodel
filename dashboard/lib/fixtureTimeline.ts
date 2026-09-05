import type { GoalsPick, UpcomingFixture } from "./data";
import { matchKey, UPCOMING_DISPLAY_LIMIT } from "./upcoming";

export type FixtureBucket = "past" | "today" | "preview";

export type FixtureTimeline = {
  past: UpcomingFixture[];
  today: UpcomingFixture[];
  preview: UpcomingFixture[];
};

type LoggedFixture = Pick<GoalsPick, "fixtureId" | "home" | "away" | "kickoff">;

export function kickoffMs(kickoff: string): number {
  const t = new Date(kickoff).getTime();
  return Number.isFinite(t) ? t : 0;
}

export function utcDateKey(kickoff: string): string {
  const t = new Date(kickoff);
  if (Number.isNaN(t.getTime())) return kickoff.slice(0, 10);
  return t.toISOString().slice(0, 10);
}

export function todayDateKey(nowMs = Date.now()): string {
  return new Date(nowMs).toISOString().slice(0, 10);
}

export function classifyFixture(kickoff: string, nowMs = Date.now()): FixtureBucket {
  const t = kickoffMs(kickoff);
  if (t <= nowMs) return "past";
  if (utcDateKey(kickoff) === todayDateKey(nowMs)) return "today";
  return "preview";
}

function mergeUpcomingFixtures(
  calendar: UpcomingFixture[],
  logged: LoggedFixture[]
): UpcomingFixture[] {
  const byKey = new Map<string, UpcomingFixture>();

  const consider = (f: UpcomingFixture) => {
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
  for (const p of logged) {
    consider({
      fixtureId: p.fixtureId,
      home: p.home,
      away: p.away,
      kickoff: p.kickoff,
    });
  }

  return [...byKey.values()].sort(
    (a, b) =>
      kickoffMs(a.kickoff) - kickoffMs(b.kickoff) ||
      a.home.localeCompare(b.home)
  );
}

export function buildFixtureTimeline(
  calendar: UpcomingFixture[],
  logged: LoggedFixture[],
  limit = UPCOMING_DISPLAY_LIMIT,
  nowMs = Date.now()
): FixtureTimeline {
  const merged = mergeUpcomingFixtures(calendar, logged);
  const past: UpcomingFixture[] = [];
  const today: UpcomingFixture[] = [];
  const preview: UpcomingFixture[] = [];

  for (const f of merged) {
    const bucket = classifyFixture(f.kickoff, nowMs);
    if (bucket === "past") past.push(f);
    else if (bucket === "today") today.push(f);
    else preview.push(f);
  }

  return {
    past,
    today,
    preview: preview.slice(0, limit),
  };
}

export function sortPastByKickoff<T extends { kickoff: string }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => kickoffMs(a.kickoff) - kickoffMs(b.kickoff));
}

export function findLoggedFixture<T extends LoggedFixture>(
  fixture: UpcomingFixture,
  logged: T[]
): T | undefined {
  const key = matchKey(fixture.home, fixture.away, fixture.kickoff);
  return (
    logged.find((g) => g.fixtureId === fixture.fixtureId) ??
    logged.find((g) => matchKey(g.home, g.away, g.kickoff) === key)
  );
}
