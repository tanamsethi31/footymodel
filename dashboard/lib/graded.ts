import type { GoalsPick, GradedResult } from "./data";
import { kickoffMs } from "./fixtureTimeline";
import { matchKey } from "./upcoming";

export function findGradedResult(
  pick: Pick<GoalsPick, "fixtureId" | "home" | "away" | "kickoff">,
  graded: GradedResult[]
): GradedResult | null {
  const byId = graded.find((g) => g.fixtureId === pick.fixtureId);
  if (byId) return byId;
  const key = matchKey(pick.home, pick.away, pick.kickoff);
  return graded.find((g) => matchKey(g.home, g.away, g.kickoff) === key) ?? null;
}

export function buildGradedKeys(graded: GradedResult[]): Set<string> {
  const keys = new Set<string>();
  for (const g of graded) {
    keys.add(g.fixtureId);
    keys.add(matchKey(g.home, g.away, g.kickoff));
  }
  return keys;
}

export function gradedByFixtureId(graded: GradedResult[]): Map<string, GradedResult> {
  const map = new Map<string, GradedResult>();
  for (const g of graded) {
    map.set(g.fixtureId, g);
    map.set(matchKey(g.home, g.away, g.kickoff), g);
  }
  return map;
}

/** Most recently completed first: latest PL kickoff at the top. */
export function sortPastPredictions<
  T extends { kickoff: string; home?: string },
>(rows: T[]): T[] {
  return [...rows].sort((a, b) => {
    const byKickoff = kickoffMs(b.kickoff) - kickoffMs(a.kickoff);
    if (byKickoff !== 0) return byKickoff;
    return (a.home ?? "").localeCompare(b.home ?? "");
  });
}

export function sortGradedResults(graded: GradedResult[]): GradedResult[] {
  return sortPastPredictions(graded);
}
