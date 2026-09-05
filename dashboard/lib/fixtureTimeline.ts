import type { GoalsPick, UpcomingFixture } from "./data";
import { matchKey, UPCOMING_DISPLAY_LIMIT } from "./upcoming";

export type FixtureBucket = "past" | "today" | "preview";

export type FixtureTimeline = {
  past: UpcomingFixture[];
  today: UpcomingFixture[];
  preview: UpcomingFixture[];
};

export type FixtureRef = Pick<UpcomingFixture, "fixtureId" | "home" | "away" | "kickoff">;

type LoggedFixture = Pick<GoalsPick, "fixtureId" | "home" | "away" | "kickoff">;

/** Typical PL match length + half-time + stoppage before treating as finished. */
export const MATCH_FINISH_BUFFER_MS = 2.5 * 60 * 60 * 1000;

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

export function isFixtureGraded(
  fixture: FixtureRef,
  gradedKeys: Set<string>
): boolean {
  return (
    gradedKeys.has(fixture.fixtureId) ||
    gradedKeys.has(matchKey(fixture.home, fixture.away, fixture.kickoff))
  );
}

export function isFixtureFinished(
  kickoff: string,
  nowMs = Date.now(),
  gradedKeys: Set<string> = new Set(),
  fixture?: FixtureRef
): boolean {
  if (fixture && isFixtureGraded(fixture, gradedKeys)) return true;
  if (utcDateKey(kickoff) < todayDateKey(nowMs)) return true;
  return kickoffMs(kickoff) + MATCH_FINISH_BUFFER_MS <= nowMs;
}

export function isFixtureLive(
  kickoff: string,
  nowMs = Date.now(),
  gradedKeys: Set<string> = new Set(),
  fixture?: FixtureRef
): boolean {
  const started = kickoffMs(kickoff) <= nowMs;
  return started && !isFixtureFinished(kickoff, nowMs, gradedKeys, fixture);
}

export function classifyFixture(
  kickoff: string,
  nowMs = Date.now(),
  gradedKeys: Set<string> = new Set(),
  fixture?: FixtureRef
): FixtureBucket {
  if (isFixtureFinished(kickoff, nowMs, gradedKeys, fixture)) return "past";
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
  nowMs = Date.now(),
  gradedKeys: Set<string> = new Set()
): FixtureTimeline {
  const merged = mergeUpcomingFixtures(calendar, logged);
  const past: UpcomingFixture[] = [];
  const today: UpcomingFixture[] = [];
  const preview: UpcomingFixture[] = [];

  for (const f of merged) {
    const bucket = classifyFixture(f.kickoff, nowMs, gradedKeys, f);
    if (bucket === "past") past.push(f);
    else if (bucket === "today") today.push(f);
    else preview.push(f);
  }

  today.sort((a, b) => {
    const aLive = isFixtureLive(a.kickoff, nowMs, gradedKeys, a);
    const bLive = isFixtureLive(b.kickoff, nowMs, gradedKeys, b);
    if (aLive !== bLive) return aLive ? -1 : 1;
    return kickoffMs(a.kickoff) - kickoffMs(b.kickoff);
  });

  return {
    past,
    today,
    preview: preview.slice(0, limit),
  };
}

export function sortPastByKickoff<T extends { kickoff: string }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => kickoffMs(b.kickoff) - kickoffMs(a.kickoff));
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
