"""WhoScored-scraped player-match shots/SOT data (browser DOM-extraction; the
JSON stats API blocks repeated calls, but the rendered livestatistics page
doesn't - see RESULTS.md). Superset of FBref's Phase D data: real per-player
minutes (actual substitution minute, not a flat assumption) and direct
position codes matching POSITION_GROUPS already, no group-mapping hack needed.

Raw cache: data/raw_whoscored/ws_scrape_export[_{league}][_{season}].tsv, one
file per (league, season) pair - see `_raw_path`. Tab-separated
`match_id<TAB>data`, one line per match, where `data` is
'HomeTeam@rows||AwayTeam@rows' and each row is
player_id^name^age^position^subMinute^shots^sot. subMinute is empty for a
full-90 starter, the minute subbed off for a replaced starter, the minute
came on for a used sub; unused subs have position=="Sub" and no subMinute.

WhoScored has no date field on the page itself, so dates are recovered by
matching (home_team, away_team) against the already-downloaded
football-data.co.uk season (each pair plays at home exactly once a season).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data import ROOT, PROCESSED_DIR
from .live import namematch

RAW_DIR = ROOT / "data" / "raw_whoscored"
# The first season scraped for each league (2023/24) predates the
# league+season-suffixed convention and keeps its original bare/league-only
# name; every season scraped since gets `ws_scrape_export_{league}_{season}.tsv`.
_LEGACY_SEASON = "2023/24"
_LEGACY_RAW_FILENAMES = {"E0": "ws_scrape_export.tsv", "D1": "ws_scrape_export_D1.tsv"}

# Big-5 leagues only have football-data.co.uk match dates in matches_xg.parquet
# (Understat join, see understat.py); DEFAULT_LEAGUES (mid-tier + E0) are in
# matches.parquet. E0 exists in both - matches.parquet is the proven path.
_BIG5_DATE_SOURCE = {"D1", "SP1", "I1", "F1"}


def _season_suffix(season: str) -> str:
    """'2024/25' -> '2024-2025' (matches the multi-season file naming)."""
    start = int(season.split("/")[0])
    return f"{start}-{start + 1}"


def _raw_path(league: str, season: str) -> Path:
    if season == _LEGACY_SEASON and league in _LEGACY_RAW_FILENAMES:
        return RAW_DIR / _LEGACY_RAW_FILENAMES[league]
    return RAW_DIR / f"ws_scrape_export_{league}_{_season_suffix(season)}.tsv"


def _minutes_played(pos: str, subm: str) -> float:
    if pos == "Sub":
        return 0.0 if subm == "" else 90.0 - float(subm)
    return 90.0 if subm == "" else float(subm)


def _load_raw_rows(league: str, season: str) -> pd.DataFrame:
    rows = []
    with open(_raw_path(league, season)) as f:
        for line in f:
            line = line.rstrip("\n")
            if "\t" not in line:
                continue
            match_id, data = line.split("\t", 1)
            if not match_id.isdigit() or data == "ERROR":
                continue
            blocks = data.split("||")
            if len(blocks) != 2:
                continue
            for side, block in zip(("h", "a"), blocks):
                if "@" not in block:
                    continue
                team, rows_str = block.split("@", 1)
                if not rows_str:
                    continue
                for row_str in rows_str.split(","):
                    pid, name, age, pos, subm, shots, sot = row_str.split("^")
                    minutes = _minutes_played(pos, subm)
                    if minutes <= 0:
                        continue  # unused sub - no signal, would poison rate denominators
                    rows.append({
                        "match_id": match_id, "team_us": team, "side": side,
                        "player_id": pid, "player": name, "position": pos,
                        "minutes": minutes, "shots": float(shots), "sot": float(sot),
                    })
    return pd.DataFrame(rows)


def _attach_dates(df: pd.DataFrame, league: str, season: str) -> pd.DataFrame:
    source = "matches_xg.parquet" if league in _BIG5_DATE_SOURCE else "matches.parquet"
    matches = pd.read_parquet(PROCESSED_DIR / source)
    fd = matches[(matches["league"] == league) & (matches["season"] == season)]
    fd_teams = sorted(set(fd["home_team"]) | set(fd["away_team"]))

    homes = (df[df["side"] == "h"][["match_id", "team_us"]].drop_duplicates("match_id")
             .rename(columns={"team_us": "home"}))
    aways = (df[df["side"] == "a"][["match_id", "team_us"]].drop_duplicates("match_id")
             .rename(columns={"team_us": "away"}))
    pairs = homes.merge(aways, on="match_id")
    pairs["home_fd"] = pairs["home"].apply(lambda t: namematch.match_team(t, fd_teams))
    pairs["away_fd"] = pairs["away"].apply(lambda t: namematch.match_team(t, fd_teams))
    pairs = pairs.merge(fd[["home_team", "away_team", "date"]],
                        left_on=["home_fd", "away_fd"],
                        right_on=["home_team", "away_team"], how="left")

    df = df.merge(pairs[["match_id", "date"]], on="match_id", how="left")
    return df.dropna(subset=["date"])


def load_players(league: str = "E0", season: str = "2023/24") -> pd.DataFrame:
    """Tidy player-match table matching the schema `SOTModel`/`LineupModel`
    already expect (match_id, date, league, team_us, side, player_id, player,
    position, minutes, shots, sot) - `team_us` is the plain team name here
    (WhoScored gives real names directly, no opaque-id recovery needed)."""
    df = _load_raw_rows(league, season)
    df = _attach_dates(df, league, season)
    df["league"] = league
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df.reset_index(drop=True)
