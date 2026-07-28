"""Configuration: data source, leagues, seasons, and column maps.

Only the ~"main" football-data.co.uk divisions carry detailed stats (shots,
shots on target, corners, cards). We deliberately target *mid-tier main* leagues
— softer lines than the PL, but still full detail — plus the PL itself as the
cleanest dataset for development/sanity checks.
"""

BASE_URL = "https://www.football-data.co.uk/mmz4281"

# Division code -> human-readable name. All of these carry detailed stats in
# recent seasons. (The obscure "extra" leagues have results + odds only and are
# intentionally excluded.)
LEAGUES = {
    "E0": "England — Premier League",
    "E1": "England — Championship",
    "E2": "England — League One",
    "E3": "England — League Two",
    "SC0": "Scotland — Premiership",
    "D1": "Germany — Bundesliga",
    "D2": "Germany — 2. Bundesliga",
    "I1": "Italy — Serie A",
    "I2": "Italy — Serie B",
    "SP1": "Spain — La Liga",
    "SP2": "Spain — Segunda",
    "F1": "France — Ligue 1",
    "F2": "France — Ligue 2",
    "N1": "Netherlands — Eredivisie",
    "B1": "Belgium — Jupiler Pro League",
    "P1": "Portugal — Primeira Liga",
    "T1": "Turkey — Super Lig",
    "G1": "Greece — Super League",
}

# Plan default: PL + mid-tier full-data leagues. Backtest picks the winner.
DEFAULT_LEAGUES = ["E0", "E1", "N1", "B1", "P1", "T1", "G1"]

# Default history: ~6 recent seasons (start years). Old data is stale; we lean
# on time-decay rather than more history. 2019 -> the 2019/20 season, etc.
DEFAULT_START_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]


def season_code(start_year: int) -> str:
    """2023 -> '2324' (football-data.co.uk season code for 2023/24)."""
    a = start_year % 100
    b = (start_year + 1) % 100
    return f"{a:02d}{b:02d}"


def season_label(start_year: int) -> str:
    """2023 -> '2023/24'."""
    return f"{start_year}/{(start_year + 1) % 100:02d}"


def csv_url(start_year: int, div: str) -> str:
    return f"{BASE_URL}/{season_code(start_year)}/{div}.csv"


# --- Column resolution --------------------------------------------------------
# football-data.co.uk column names are stable for match stats but the odds
# columns changed over the years. We resolve each target field from a
# priority-ordered list of candidate source columns (first match wins).

# Match-stat columns (present in all detailed-league CSVs).
STAT_COLUMNS = {
    "fthg": "FTHG",   # full-time home goals
    "ftag": "FTAG",   # full-time away goals
    "ftr": "FTR",     # full-time result H/D/A
    "hthg": "HTHG",   # half-time home goals
    "htag": "HTAG",
    "home_shots": "HS",
    "away_shots": "AS",
    "home_sot": "HST",  # shots on target
    "away_sot": "AST",
    "home_corners": "HC",
    "away_corners": "AC",
    "home_yellows": "HY",
    "away_yellows": "AY",
    "home_reds": "HR",
    "away_reds": "AR",
}

# Closing-odds resolution. Prefer the *average closing* line (market consensus at
# kickoff) — our benchmark for "did we find value". Fall back to Bet365 closing,
# then Pinnacle closing, then opening/average, then Bet365 opening.
# The "Bb" columns are the old Betbrain-era averages (pre ~2019).
ODDS_CANDIDATES = {
    "odds_h": ["AvgCH", "B365CH", "PSCH", "AvgH", "BbAvH", "B365H"],
    "odds_d": ["AvgCD", "B365CD", "PSCD", "AvgD", "BbAvD", "B365D"],
    "odds_a": ["AvgCA", "B365CA", "PSCA", "AvgA", "BbAvA", "B365A"],
    "odds_over25": ["AvgC>2.5", "B365C>2.5", "P>2.5", "Avg>2.5", "BbAv>2.5", "B365>2.5"],
    "odds_under25": ["AvgC<2.5", "B365C<2.5", "P<2.5", "Avg<2.5", "BbAv<2.5", "B365<2.5"],
}

# OPENING / early odds — strictly the NON-closing columns (football-data collects
# these well before kickoff). Paired with the closing odds above, these let us
# measure Closing Line Value (did the market move toward our picks?) and test
# whether the model beats the softer opening line.
ODDS_OPEN_CANDIDATES = {
    "odds_h_open": ["AvgH", "B365H", "BbAvH", "PSH"],
    "odds_d_open": ["AvgD", "B365D", "BbAvD", "PSD"],
    "odds_a_open": ["AvgA", "B365A", "BbAvA", "PSA"],
    "odds_over25_open": ["Avg>2.5", "B365>2.5", "BbAv>2.5", "P>2.5"],
    "odds_under25_open": ["Avg<2.5", "B365<2.5", "BbAv<2.5", "P<2.5"],
}

# BEST-PRICE (market maximum) odds — the best price available across all books,
# not the average. Line shopping: betting the max strips most of the margin and
# is a real market-structure edge. "_max" = closing max, "_maxopen" = opening max.
ODDS_MAX_CANDIDATES = {
    "odds_h_max": ["MaxCH"], "odds_d_max": ["MaxCD"], "odds_a_max": ["MaxCA"],
    "odds_over25_max": ["MaxC>2.5"], "odds_under25_max": ["MaxC<2.5"],
    "odds_h_maxopen": ["MaxH"], "odds_d_maxopen": ["MaxD"], "odds_a_maxopen": ["MaxA"],
    "odds_over25_maxopen": ["Max>2.5"], "odds_under25_maxopen": ["Max<2.5"],
}

# ASIAN HANDICAP (Phase C). `ah_line` is the handicap applied to the HOME team
# (e.g. -0.75 means home must win by 1+ for a full cover, with a half-stake
# push at a 0-goal margin). Quarter lines (x.25/x.75) split the stake across
# two adjacent half/whole lines — settlement logic lives in model.py, not here.
ODDS_AH_CANDIDATES = {
    "ah_line": ["AHCh", "AHh"],            # closing preferred, opening fallback
    "ah_line_open": ["AHh"],
    "ah_odds_h": ["AvgCAHH", "B365CAHH", "PCAHH", "AvgAHH", "B365AHH"],
    "ah_odds_a": ["AvgCAHA", "B365CAHA", "PCAHA", "AvgAHA", "B365AHA"],
    "ah_odds_h_open": ["AvgAHH", "B365AHH", "PAHH"],
    "ah_odds_a_open": ["AvgAHA", "B365AHA", "PAHA"],
    "ah_odds_h_max": ["MaxCAHH"],
    "ah_odds_a_max": ["MaxCAHA"],
    "ah_odds_h_maxopen": ["MaxAHH"],
    "ah_odds_a_maxopen": ["MaxAHA"],
}
