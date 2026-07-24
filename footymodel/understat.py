"""Phase 2b — Understat xG integration.

Understat covers only the big-5 leagues (+ Russia). It exposes match data via
    https://understat.com/getLeagueData/{league}/{year}
(requires an XMLHttpRequest header). Each match carries teams, goals and xG.

We join xG onto the football-data.co.uk matches by (date, score) rather than by
team name — team names differ across sources ("Man City" vs "Manchester City")
and the score+date key is unambiguous within a league-season (with a fuzzy
team-name tiebreak for the rare same-day/same-score collision).

Usage:
    python -m footymodel.understat            # fetch + merge -> matches_xg.parquet
"""
from __future__ import annotations

import argparse
import time
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests

from . import config
from . import data as data_mod

# football-data division -> Understat league code.
DIV_TO_UNDERSTAT = {
    "E0": "EPL",
    "SP1": "La_liga",
    "D1": "Bundesliga",
    "I1": "Serie_A",
    "F1": "Ligue_1",
}
XG_LEAGUES = list(DIV_TO_UNDERSTAT.keys())

RAW_XG_DIR = data_mod.ROOT / "data" / "raw_understat"
XG_OUTPUT = data_mod.PROCESSED_DIR / "matches_xg.parquet"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (footymodel research)",
    "Referer": "https://understat.com/",
    "X-Requested-With": "XMLHttpRequest",
}


def fetch_league_season(us_league: str, year: int, refresh: bool = False) -> list[dict]:
    """Fetch + cache one Understat league-season; return match-level records."""
    RAW_XG_DIR.mkdir(parents=True, exist_ok=True)
    cache = RAW_XG_DIR / f"{us_league}_{year}.json"
    if cache.exists() and not refresh:
        raw = cache.read_text()
    else:
        url = f"https://understat.com/getLeagueData/{us_league}/{year}"
        resp = requests.get(url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        raw = resp.text
        cache.write_text(raw)
        time.sleep(0.6)  # be polite

    import json
    payload = json.loads(raw)
    out = []
    for d in payload.get("dates", []):
        if not d.get("isResult"):
            continue
        out.append({
            "date": pd.Timestamp(d["datetime"]).normalize(),
            "home_us": d["h"]["title"],
            "away_us": d["a"]["title"],
            "home_goals": int(d["goals"]["h"]),
            "away_goals": int(d["goals"]["a"]),
            "home_xg": float(d["xG"]["h"]),
            "away_xg": float(d["xG"]["a"]),
        })
    return out


def fetch_xg(divs: list[str], start_years: list[int], refresh: bool = False) -> pd.DataFrame:
    frames = []
    for div in divs:
        us = DIV_TO_UNDERSTAT[div]
        for yr in start_years:
            try:
                recs = fetch_league_season(us, yr, refresh=refresh)
            except requests.RequestException as exc:
                print(f"  ! {us} {yr}: fetch failed ({exc})")
                continue
            if not recs:
                print(f"  - {us} {yr}: no results")
                continue
            df = pd.DataFrame(recs)
            df["league"] = div
            df["season"] = config.season_label(yr)
            frames.append(df)
            print(f"  + {us} {config.season_label(yr)}: {len(df)} matches")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def merge_xg(matches: pd.DataFrame, xg: pd.DataFrame) -> pd.DataFrame:
    """Attach home_xg/away_xg to `matches` by (league, date, score).

    Team names are only used to break the rare same-day/same-score tie.
    Returns `matches` with two new columns (NaN where no xG match found).
    """
    matches = matches.copy()
    matches["home_xg"] = pd.NA
    matches["away_xg"] = pd.NA

    xg = xg.copy()
    xg["date"] = pd.to_datetime(xg["date"]).dt.normalize()

    matched = 0
    for lg in xg["league"].unique():
        m_idx = matches.index[matches["league"] == lg]
        x_lg = xg[xg["league"] == lg]
        # index xg by (date, hg, ag) -> list of candidate rows
        buckets: dict[tuple, list] = {}
        for row in x_lg.itertuples(index=False):
            buckets.setdefault((row.date, row.home_goals, row.away_goals), []).append(row)

        for i in m_idx:
            mrow = matches.loc[i]
            if pd.isna(mrow["date"]) or pd.isna(mrow["fthg"]) or pd.isna(mrow["ftag"]):
                continue
            key = (pd.Timestamp(mrow["date"]).normalize(), int(mrow["fthg"]), int(mrow["ftag"]))
            cands = buckets.get(key, [])
            if not cands:
                continue
            if len(cands) == 1:
                best = cands[0]
            else:  # tiebreak on home-team-name similarity
                best = max(cands, key=lambda c: _similar(str(mrow["home_team"]), c.home_us))
            matches.at[i, "home_xg"] = best.home_xg
            matches.at[i, "away_xg"] = best.away_xg
            matched += 1

    matches["home_xg"] = pd.to_numeric(matches["home_xg"], errors="coerce")
    matches["away_xg"] = pd.to_numeric(matches["away_xg"], errors="coerce")
    print(f"\nMerged xG onto {matched} matches.")
    return matches


def build(divs: list[str], start_years: list[int], refresh: bool = False) -> pd.DataFrame:
    """Build football-data matches for the xG leagues, merge Understat xG, save."""
    print("Downloading football-data for xG leagues...")
    matches = data_mod.build_dataset(divs, start_years, refresh=refresh)
    print("\nFetching Understat xG...")
    xg = fetch_xg(divs, start_years, refresh=refresh)
    merged = merge_xg(matches, xg)

    covered = merged[merged["league"].isin(divs)]
    rate = covered["home_xg"].notna().mean() * 100
    print(f"xG coverage on {len(covered)} big-5 matches: {rate:.1f}%")
    merged.to_parquet(XG_OUTPUT, index=False)
    print(f"Saved -> {XG_OUTPUT}")
    return merged


def load_xg() -> pd.DataFrame:
    return pd.read_parquet(XG_OUTPUT)


def main():
    p = argparse.ArgumentParser(description="Fetch Understat xG and merge onto matches.")
    p.add_argument("--leagues", nargs="+", default=XG_LEAGUES,
                   help=f"xG-covered divisions (default: {' '.join(XG_LEAGUES)})")
    p.add_argument("--seasons", nargs="+", type=int, default=config.DEFAULT_START_YEARS)
    p.add_argument("--refresh", action="store_true")
    args = p.parse_args()
    build(args.leagues, args.seasons, refresh=args.refresh)


if __name__ == "__main__":
    main()
