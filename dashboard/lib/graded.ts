import type { GoalsPick, GradedResult } from "./data";
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

export function gradedByFixtureId(graded: GradedResult[]): Map<string, GradedResult> {
  const map = new Map<string, GradedResult>();
  for (const g of graded) {
    map.set(g.fixtureId, g);
    map.set(matchKey(g.home, g.away, g.kickoff), g);
  }
  return map;
}
