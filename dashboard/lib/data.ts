import Papa from "papaparse";

// The footymodel repo is private, so raw.githubusercontent.com 404s
// unauthenticated - fetch through the GitHub Contents API instead, which
// accepts the same GITHUB_TOKEN used for API access.
const REPO = "tanamsethi31/footymodel";
const DATA_PATH = "data/processed";

export type GoalsPick = {
  loggedAt: string;
  fixtureId: string;
  league: string;
  kickoff: string;
  home: string;
  away: string;
  nHomeMatched: number;
  nAwayMatched: number;
  modelPOver25: number;
  expTotalGoals: number;
  oddsOver25: number | null;
  oddsUnder25: number | null;
  source: string | null;
  fairPOver25: number | null;
  evOver25: number | null;
  evUnder25: number | null;
};

export type GradedResult = {
  fixtureId: string;
  home: string;
  away: string;
  kickoff: string;
  actualHomeGoals: number;
  actualAwayGoals: number;
  actualTotalGoals: number;
  actualOverWon: boolean;
  modelPOver25: number;
  modelCorrect: boolean;
  betSide: "over" | "under" | null;
  betOdds: number | null;
  betWon: boolean | null;
  realizedReturn: number | null;
  gradedAt: string;
};

export type PropsPick = {
  fixtureId: string;
  kickoff: string;
  team: string;
  player: string;
  pShotsGt05: number | null;
  oddsShotsGt05: number | null;
  evShotsGt05: number | null;
  pShotsGt15: number | null;
  oddsShotsGt15: number | null;
  evShotsGt15: number | null;
  pShotsGt25: number | null;
  oddsShotsGt25: number | null;
  evShotsGt25: number | null;
  pSotGt05: number | null;
  oddsSotGt05: number | null;
  evSotGt05: number | null;
  pSotGt15: number | null;
  oddsSotGt15: number | null;
  evSotGt15: number | null;
};

function num(v: unknown): number | null {
  if (v === undefined || v === null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

// pandas' to_csv writes Python bools as "True"/"False" (capitalized), not
// JSON-style "true"/"false".
function bool(v: unknown): boolean | null {
  if (v === "True") return true;
  if (v === "False") return false;
  return null;
}

async function fetchCsv(name: string): Promise<Record<string, string>[]> {
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw new Error("GITHUB_TOKEN not set");
  const res = await fetch(
    `https://api.github.com/repos/${REPO}/contents/${DATA_PATH}/${name}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github.raw+json",
      },
      // Revalidate frequently - predictions only land a few times a day,
      // but this keeps the dashboard feeling live without hammering the API.
      next: { revalidate: 60 },
    }
  );
  if (res.status === 404) return []; // file doesn't exist yet (no rows logged)
  if (!res.ok) throw new Error(`Failed to fetch ${name}: ${res.status} ${await res.text()}`);
  const text = await res.text();
  const parsed = Papa.parse<Record<string, string>>(text, {
    header: true,
    skipEmptyLines: true,
  });
  return parsed.data;
}

// The goals CSV's header was written by the FIRST row ever appended
// (before source/fair_p_over25/ev_over25/ev_under25 existed as columns),
// and pandas' `to_csv(mode="a")` never rewrites the header - so older
// rows have 12 fields, newer ones have 16. Papaparse puts any fields
// beyond the header into a `__parsed_extra` array (verified directly,
// NOT positionally-keyed properties as a first guess assumed) - this
// maps those back to their real names rather than dropping them.
const GOALS_EXTRA_COLS = ["source", "fair_p_over25", "ev_over25", "ev_under25"];

type RowWithExtra = Record<string, string> & { __parsed_extra?: string[] };

export async function getGoalsPicks(): Promise<GoalsPick[]> {
  const rows = (await fetchCsv("live_recommendations.csv")) as RowWithExtra[];
  return rows
    .map((r) => {
      const extra: Record<string, string> = {};
      (r.__parsed_extra ?? []).forEach((val, i) => {
        if (GOALS_EXTRA_COLS[i] !== undefined) extra[GOALS_EXTRA_COLS[i]] = val;
      });
      return {
        loggedAt: r.logged_at,
        fixtureId: r.fixture_id,
        league: r.league,
        kickoff: r.kickoff,
        home: r.home,
        away: r.away,
        nHomeMatched: num(r.n_home_starters_matched) ?? 0,
        nAwayMatched: num(r.n_away_starters_matched) ?? 0,
        modelPOver25: num(r.model_p_over25) ?? 0,
        expTotalGoals: num(r.exp_total_goals) ?? 0,
        oddsOver25: num(r.odds_over25),
        oddsUnder25: num(r.odds_under25),
        source: extra.source ?? "api-football",
        fairPOver25: num(extra.fair_p_over25),
        evOver25: num(extra.ev_over25),
        evUnder25: num(extra.ev_under25),
      };
    })
    .filter((p) => p.fixtureId)
    .sort((a, b) => (a.kickoff < b.kickoff ? 1 : -1));
}

export async function getPropsPicks(): Promise<PropsPick[]> {
  const rows = await fetchCsv("live_player_props.csv");
  return rows
    .map((r) => ({
      fixtureId: r.fixture_id,
      kickoff: r.kickoff,
      team: r.team,
      player: r.player,
      pShotsGt05: num(r["p_shots_gt0.5"]),
      oddsShotsGt05: num(r["odds_shots_gt0.5"]),
      evShotsGt05: num(r["ev_shots_gt0.5"]),
      pShotsGt15: num(r["p_shots_gt1.5"]),
      oddsShotsGt15: num(r["odds_shots_gt1.5"]),
      evShotsGt15: num(r["ev_shots_gt1.5"]),
      pShotsGt25: num(r["p_shots_gt2.5"]),
      oddsShotsGt25: num(r["odds_shots_gt2.5"]),
      evShotsGt25: num(r["ev_shots_gt2.5"]),
      pSotGt05: num(r["p_sot_gt0.5"]),
      oddsSotGt05: num(r["odds_sot_gt0.5"]),
      evSotGt05: num(r["ev_sot_gt0.5"]),
      pSotGt15: num(r["p_sot_gt1.5"]),
      oddsSotGt15: num(r["odds_sot_gt1.5"]),
      evSotGt15: num(r["ev_sot_gt1.5"]),
    }))
    .filter((p) => p.fixtureId)
    .sort((a, b) => (a.kickoff < b.kickoff ? 1 : -1));
}

export async function getGradedResults(): Promise<GradedResult[]> {
  const rows = await fetchCsv("graded_results.csv");
  return rows
    .map((r) => ({
      fixtureId: r.fixture_id,
      home: r.home,
      away: r.away,
      kickoff: r.kickoff,
      actualHomeGoals: num(r.actual_home_goals) ?? 0,
      actualAwayGoals: num(r.actual_away_goals) ?? 0,
      actualTotalGoals: num(r.actual_total_goals) ?? 0,
      actualOverWon: bool(r.actual_over_won) ?? false,
      modelPOver25: num(r.model_p_over25) ?? 0,
      modelCorrect: bool(r.model_correct) ?? false,
      betSide: (r.bet_side === "over" || r.bet_side === "under" ? r.bet_side : null) as
        | "over"
        | "under"
        | null,
      betOdds: num(r.bet_odds),
      betWon: bool(r.bet_won),
      realizedReturn: num(r.realized_return),
      gradedAt: r.graded_at,
    }))
    .filter((r) => r.fixtureId)
    .sort((a, b) => (a.kickoff < b.kickoff ? 1 : -1));
}
