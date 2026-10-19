import type { GradedPropsPlayer, PropsPick } from "./data";

/** Model lines use 0.5 / 1.5 / 2.5; UI labels are 1+ / 2+ / 3+. */
export const SHOTS_LINES = [0.5, 1.5, 2.5] as const;
export const SOT_LINES = [0.5, 1.5] as const;

export function hitOver(actual: number | null, line: number): boolean | null {
  if (actual === null || actual === undefined) return null;
  return actual > line;
}

export function shotsProbAt(row: PropsPick | GradedPropsPlayer, idx: number): number | null {
  const keys = ["pShotsGt05", "pShotsGt15", "pShotsGt25"] as const;
  return row[keys[idx]] ?? null;
}

export function sotProbAt(row: PropsPick | GradedPropsPlayer, idx: number): number | null {
  const keys = ["pSotGt05", "pSotGt15"] as const;
  return row[keys[idx]] ?? null;
}

/** Build props table rows from graded output when live_player_props has no block. */
export function propsRowsFromGrades(
  fixture: { fixtureId: string; kickoff: string; home: string; away: string },
  grades: GradedPropsPlayer[]
): PropsPick[] {
  return grades.map((g) => ({
    fixtureId: fixture.fixtureId,
    kickoff: fixture.kickoff,
    home: fixture.home,
    away: fixture.away,
    team: g.team,
    player: g.player,
    pShotsGt05: g.pShotsGt05,
    pShotsGt15: g.pShotsGt15,
    pShotsGt25: g.pShotsGt25,
    oddsShotsGt05: null,
    oddsShotsGt15: null,
    oddsShotsGt25: null,
    evShotsGt05: null,
    evShotsGt15: null,
    evShotsGt25: null,
    pSotGt05: g.pSotGt05,
    pSotGt15: g.pSotGt15,
    oddsSotGt05: null,
    oddsSotGt15: null,
    evSotGt05: null,
    evSotGt15: null,
  }));
}
