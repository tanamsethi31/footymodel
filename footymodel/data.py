"""Phase 1 — data pipeline.

Download football-data.co.uk CSVs for the configured leagues/seasons and
normalize them into one tidy table (one row per match) with a stable,
league-agnostic schema. Closing odds are preserved as our value benchmark.

Usage:
    python -m footymodel.data
    python -m footymodel.data --leagues E0 E1 N1 --seasons 2021 2022 2023 2024
    python -m footymodel.data --refresh          # re-download even if cached
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path

import pandas as pd
import requests

from . import config

# Project paths (repo root is two levels up from this file).
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "matches.parquet"

# football-data.co.uk blocks default python-requests UA on occasion; use a
# browser-like UA to be polite and reliable.
_HEADERS = {"User-Agent": "Mozilla/5.0 (footymodel data pipeline; research use)"}

# Non-odds identity columns that must be present for a usable detailed CSV.
_REQUIRED_SOURCE_COLS = ["HomeTeam", "AwayTeam", "FTHG", "FTAG"]


def _resolve(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    """Return the first candidate column that exists in df, else None."""
    for col in candidates:
        if col in df.columns:
            return df[col]
    return None


def download_csv(start_year: int, div: str, refresh: bool = False) -> Path | None:
    """Download one season/division CSV to data/raw/, with caching.

    Returns the local path, or None if the download failed or 404'd (some
    league/season combinations simply don't exist).
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    local = RAW_DIR / f"{div}_{config.season_code(start_year)}.csv"
    if local.exists() and not refresh:
        return local

    url = config.csv_url(start_year, div)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=30)
    except requests.RequestException as exc:
        print(f"  ! {div} {config.season_label(start_year)}: request failed ({exc})")
        return None

    if resp.status_code != 200 or not resp.content.strip():
        print(f"  - {div} {config.season_label(start_year)}: not available (HTTP {resp.status_code})")
        return None

    local.write_bytes(resp.content)
    return local


def _read_raw(path: Path) -> pd.DataFrame | None:
    """Read a raw CSV robustly (encoding + stray trailing columns/rows)."""
    for enc in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=enc, on_bad_lines="skip")
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    else:
        return None

    # Drop fully-empty rows and any without the core identity columns.
    if not all(c in df.columns for c in _REQUIRED_SOURCE_COLS):
        return None
    df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
    return df if len(df) else None


def normalize(df: pd.DataFrame, start_year: int, div: str) -> pd.DataFrame:
    """Map a raw football-data CSV onto the tidy schema."""
    out = pd.DataFrame()
    out["league"] = df.get("Div", pd.Series([div] * len(df), index=df.index))
    out["league_name"] = config.LEAGUES.get(div, div)
    out["season"] = config.season_label(start_year)

    # Dates arrive as dd/mm/yy or dd/mm/yyyy; dayfirst handles both.
    out["date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    out["home_team"] = df["HomeTeam"].astype(str).str.strip()
    out["away_team"] = df["AwayTeam"].astype(str).str.strip()

    for target, source in config.STAT_COLUMNS.items():
        if source in df.columns:
            out[target] = df[source]
        else:
            out[target] = pd.NA

    for target, candidates in config.ODDS_CANDIDATES.items():
        series = _resolve(df, candidates)
        out[target] = series.values if series is not None else pd.NA

    # Numeric coercion for everything except identity/result string columns.
    numeric = [c for c in out.columns
               if c not in ("league", "league_name", "season", "date",
                            "home_team", "away_team", "ftr")]
    for c in numeric:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out.dropna(subset=["date"]).reset_index(drop=True)
    return out


def drop_invalid_odds(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose 1X2 closing odds are internally impossible.

    A genuine bookmaker line always has a positive margin, so the implied
    probabilities (1/odds) must sum to >= 1. Rows below that are data errors
    (mis-keyed odds) and would poison margin-stripping in Phase 3. Rows missing
    odds are left untouched — they're handled downstream, not corrupt.
    """
    have_all = df[["odds_h", "odds_d", "odds_a"]].notna().all(axis=1)
    overround = 1 / df["odds_h"] + 1 / df["odds_d"] + 1 / df["odds_a"]
    bad = have_all & (overround < 1.0)
    if bad.any():
        print(f"  ! dropping {int(bad.sum())} rows with impossible 1X2 odds (overround < 1)")
    return df.loc[~bad].reset_index(drop=True)


def build_dataset(leagues: list[str], start_years: list[int],
                  refresh: bool = False) -> pd.DataFrame:
    """Download + normalize + concatenate all requested league/season files."""
    frames: list[pd.DataFrame] = []
    for div in leagues:
        for year in start_years:
            path = download_csv(year, div, refresh=refresh)
            if path is None:
                continue
            raw = _read_raw(path)
            if raw is None:
                print(f"  - {div} {config.season_label(year)}: unusable/empty file")
                continue
            tidy = normalize(raw, year, div)
            frames.append(tidy)
            print(f"  + {div} {config.season_label(year)}: {len(tidy)} matches")

    if not frames:
        raise RuntimeError("No data downloaded — check connectivity or league/season args.")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["date", "league"]).reset_index(drop=True)
    combined = drop_invalid_odds(combined)
    return combined


def save(df: pd.DataFrame, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load(path: Path = OUTPUT_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def _summarize(df: pd.DataFrame) -> None:
    print("\n=== Dataset summary ===")
    print(f"Total matches : {len(df):,}")
    print(f"Date range    : {df['date'].min().date()} -> {df['date'].max().date()}")
    print(f"Leagues       : {df['league'].nunique()}  Seasons: {df['season'].nunique()}")
    have_sot = df["home_sot"].notna().mean() * 100
    have_1x2 = df["odds_h"].notna().mean() * 100
    have_ou = df["odds_over25"].notna().mean() * 100
    print(f"Rows w/ shots-on-target: {have_sot:5.1f}%")
    print(f"Rows w/ 1X2 closing odds: {have_1x2:5.1f}%")
    print(f"Rows w/ O/U 2.5 closing : {have_ou:5.1f}%")
    print("\nMatches per league:")
    for div, n in df["league"].value_counts().sort_index().items():
        print(f"  {div:4s} {config.LEAGUES.get(div, div):32s} {n:5d}")


def main() -> None:
    p = argparse.ArgumentParser(description="Download + normalize football-data.co.uk match data.")
    p.add_argument("--leagues", nargs="+", default=config.DEFAULT_LEAGUES,
                   help=f"Division codes (default: {' '.join(config.DEFAULT_LEAGUES)})")
    p.add_argument("--seasons", nargs="+", type=int, default=config.DEFAULT_START_YEARS,
                   help="Season START years, e.g. 2023 for 2023/24")
    p.add_argument("--refresh", action="store_true", help="Re-download even if cached")
    args = p.parse_args()

    print(f"Leagues: {args.leagues}")
    print(f"Seasons: {[config.season_label(y) for y in args.seasons]}\n")
    df = build_dataset(args.leagues, args.seasons, refresh=args.refresh)
    save(df)
    _summarize(df)
    print(f"\nSaved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
