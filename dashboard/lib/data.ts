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

export type MatchDetail = {
  fixtureId: string;
  homeStarters: string[];
  awayStarters: string[];
  expTeam: number;
  expFull: number;
  pOver25Team: number;
  pOver25Full: number;
};

export type UpcomingFixture = {
  fixtureId: string;
  home: string;
  away: string;
  kickoff: string;
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

export type KellySimResult = {
  strategy: string;
  kellyMult: number | null;
  nTrials: number;
  nBets: number;
  startBankroll: number;
  medianFinalBankroll: number;
  p5FinalBankroll: number;
  p95FinalBankroll: number;
  medianMaxDrawdown: number;
  ruinProbability: number;
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

export type MostProbablePick = {
  fixtureId: string;
  kickoff: string;
  player: string;
  team: string;
  marketLabel: string;
  prob: number;
  odds: number | null;
};

const PROP_MARKETS: {
  key: keyof PropsPick;
  oddsKey: keyof PropsPick;
  label: string;
}[] = [
  { key: "pShotsGt05", oddsKey: "oddsShotsGt05", label: "Shots 1+" },
  { key: "pShotsGt15", oddsKey: "oddsShotsGt15", label: "Shots 2+" },
  { key: "pShotsGt25", oddsKey: "oddsShotsGt25", label: "Shots 3+" },
  { key: "pSotGt05", oddsKey: "oddsSotGt05", label: "SOT 1+" },
  { key: "pSotGt15", oddsKey: "oddsSotGt15", label: "SOT 2+" },
];

export function getMostProbablePicks(
  props: PropsPick[],
  limit = 8
): MostProbablePick[] {
  const picks: MostProbablePick[] = [];
  for (const row of props) {
    for (const m of PROP_MARKETS) {
      const p = row[m.key] as number | null;
      if (p === null) continue;
      picks.push({
        fixtureId: row.fixtureId,
        kickoff: row.kickoff,
        player: row.player,
        team: row.team,
        marketLabel: m.label,
        prob: p,
        odds: row[m.oddsKey] as number | null,
      });
    }
  }
  return picks.sort((a, b) => b.prob - a.prob).slice(0, limit);
}

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

async function fetchJsonl(name: string): Promise<Record<string, unknown>[]> {
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw new Error("GITHUB_TOKEN not set");
  const res = await fetch(
    `https://api.github.com/repos/${REPO}/contents/${DATA_PATH}/${name}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github.raw+json",
      },
      next: { revalidate: 60 },
    }
  );
  if (res.status === 404) return []; // file doesn't exist yet (no rows logged)
  if (!res.ok) throw new Error(`Failed to fetch ${name}: ${res.status} ${await res.text()}`);
  const text = await res.text();
  return text
    .split("\n")
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line));
}

async function fetchJson(name: string): Promise<unknown[]> {
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw new Error("GITHUB_TOKEN not set");
  const res = await fetch(
    `https://api.github.com/repos/${REPO}/contents/${DATA_PATH}/${name}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github.raw+json",
      },
      next: { revalidate: 60 },
    }
  );
  if (res.status === 404) return []; // file doesn't exist yet
  if (!res.ok) throw new Error(`Failed to fetch ${name}: ${res.status} ${await res.text()}`);
  const text = await res.text();
  return JSON.parse(text);
}

// The goals CSV's header was written by the FIRST row ever appended
// (before source/fair_p_over25/ev_over25/ev_under25 existed as columns),
// and pandas' `to_csv(mode="a")` never rewrites the header - so rows have
// a ragged number of trailing fields depending on which engine logged them
// AND whether odds were available at the time:
//   - engine.py never writes "source" at all -> 0 extra fields (no odds)
//     or 3 (fair_p/ev_over/ev_under, all-or-nothing together)
//   - rapidapi_engine.py / sofascore_engine.py always write "source" ->
//     1 extra field (source only, no odds) or 4 (source + the same triple)
// These four lengths (0/1/3/4) never collide, so the row's field count
// alone tells us which fields are actually present - a fixed positional
// mapping (assuming "source" always comes first) previously misread
// engine.py's 3-field rows, shifting fair_p/ev_over/ev_under left by one
// and silently corrupting the EV badges for every API-Football-sourced
// prediction that had real odds (caught 2026-08-28 on the first such row:
// Crystal Palace v Man City rendered ev_under25's value in the ev_over25
// slot, with ev_under25 itself blank).
const GOALS_TRIPLE_COLS = ["fair_p_over25", "ev_over25", "ev_under25"] as const;

type RowWithExtra = Record<string, string> & { __parsed_extra?: string[] };

export async function getGoalsPicks(): Promise<GoalsPick[]> {
  const rows = (await fetchCsv("live_recommendations.csv")) as RowWithExtra[];
  return rows
    .map((r) => {
      const parsedExtra = r.__parsed_extra ?? [];
      const n = parsedExtra.length;
      const extra: Record<string, string> = {};
      if (n === 1 || n === 4) extra.source = parsedExtra[0];
      if (n === 3 || n === 4) {
        const tripleStart = n - 3;
        GOALS_TRIPLE_COLS.forEach((col, i) => {
          extra[col] = parsedExtra[tripleStart + i];
        });
      }
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

export async function getMatchDetails(): Promise<Record<string, MatchDetail>> {
  const rows = await fetchJsonl("match_detail.jsonl");
  const byFixtureId: Record<string, MatchDetail> = {};
  for (const r of rows) {
    // A malformed/partial line (e.g. an interrupted write) should degrade to
    // "no detail for this match", the same as a fixture with no line at all -
    // not render NaN through pct()/toFixed() in the UI.
    const expTeam = num(r.exp_team);
    const expFull = num(r.exp_full);
    const pOver25Team = num(r.p_over25_team);
    const pOver25Full = num(r.p_over25_full);
    if (expTeam === null || expFull === null || pOver25Team === null || pOver25Full === null) {
      continue;
    }
    const fixtureId = String(r.fixture_id);
    byFixtureId[fixtureId] = {
      fixtureId,
      homeStarters: Array.isArray(r.home_starters) ? (r.home_starters as string[]) : [],
      awayStarters: Array.isArray(r.away_starters) ? (r.away_starters as string[]) : [],
      expTeam,
      expFull,
      pOver25Team,
      pOver25Full,
    };
  }
  return byFixtureId;
}

export async function getUpcomingFixtures(): Promise<UpcomingFixture[]> {
  const rows = (await fetchJson("upcoming_fixtures.json")) as Record<string, unknown>[];
  return rows
    .map((r) => ({
      fixtureId: String(r.fixture_id),
      home: String(r.home),
      away: String(r.away),
      kickoff: String(r.kickoff),
    }))
    .filter((f) => f.fixtureId && f.home && f.away);
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

export async function getKellySimResults(): Promise<KellySimResult[]> {
  const rows = await fetchCsv("kelly_simulation.csv");
  return rows
    .map((r) => ({
      strategy: r.strategy,
      kellyMult: num(r.kelly_mult),
      nTrials: num(r.n_trials) ?? 0,
      nBets: num(r.n_bets) ?? 0,
      startBankroll: num(r.start_bankroll) ?? 100,
      medianFinalBankroll: num(r.median_final_bankroll) ?? 0,
      p5FinalBankroll: num(r.p5_final_bankroll) ?? 0,
      p95FinalBankroll: num(r.p95_final_bankroll) ?? 0,
      medianMaxDrawdown: num(r.median_max_drawdown) ?? 0,
      ruinProbability: num(r.ruin_probability) ?? 0,
    }))
    .filter((r) => r.strategy)
    .sort((a, b) => (a.kellyMult ?? -1) - (b.kellyMult ?? -1));
}
