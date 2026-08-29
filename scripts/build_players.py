"""Scrape Understat per-match player rosters and save the player-match table.

Incremental by design: only scrapes the league(s)/season(s) you ask for, and
merges the result into whatever's already in PLAYER_OUTPUT (replacing just
those league-seasons if already present, leaving every other league-season
untouched). This matters because, unlike the season-level football-data.co.uk
and base-xG fetches (a handful of requests total), this scrapes ONE request
PER MATCH - re-running the full multi-season history every time (as a daily
refresh would need to, to pick up new results) would mean thousands of
redundant Understat requests a day for seasons that already finished.

Usage:
    python scripts/build_players.py E0,SP1,D1,I1,F1          # full default seasons
    python scripts/build_players.py E0,SP1,D1,I1,F1 2025      # just 2025/26
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel import config
from footymodel.understat import build_player_dataset, PLAYER_OUTPUT


def merge_player_dataset(existing: pd.DataFrame | None, new_rows: pd.DataFrame,
                         divs: list[str], years: list[int]) -> pd.DataFrame:
    """Replace just the (league, season) pairs being refreshed, keep every
    other league-season row untouched. `existing=None` (no prior file, first
    run) just returns `new_rows` as-is."""
    if existing is None:
        return new_rows
    refreshed_seasons = {config.season_label(y) for y in years}
    is_refreshed = existing["league"].isin(divs) & existing["season"].isin(refreshed_seasons)
    return pd.concat([existing[~is_refreshed], new_rows], ignore_index=True)


if __name__ == "__main__":
    DIVS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["E0"]
    YEARS = [int(y) for y in sys.argv[2].split(",")] if len(sys.argv) > 2 else config.DEFAULT_START_YEARS

    print(f"Scraping player rosters for {DIVS}, seasons {YEARS}")
    new_rows = build_player_dataset(DIVS, YEARS)
    existing = pd.read_parquet(PLAYER_OUTPUT) if PLAYER_OUTPUT.exists() else None
    df = merge_player_dataset(existing, new_rows, DIVS, YEARS)

    df.to_parquet(PLAYER_OUTPUT, index=False)
    print(f"\nSaved {len(df)} player-match rows -> {PLAYER_OUTPUT}")
    print(f"Unique players: {df['player_id'].nunique()}  matches: {df['match_id'].nunique()}")
