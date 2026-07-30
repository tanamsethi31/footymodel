"""FBref-scraped player-match data (shots + shots-on-target). Complements
Understat (which has no per-player SOT) - see scripts/shots_calibration_test.py
for the Understat-based raw-shots model this extends.

Scraped via footymodel.live-style browser fetch (FBref blocks direct requests
with Cloudflare) - see the fbref scraping notes in RESULTS.md. Raw cache:
data/raw_fbref/player_match.jsonl (one row per player-match, appended by
scripts/fbref_ingest_batch.py).
"""
from __future__ import annotations

import re

import pandas as pd

from .data import ROOT

RAW = ROOT / "data" / "raw_fbref" / "player_match.jsonl"

_MONTHS = ("January|February|March|April|May|June|July|August|September"
          "|October|November|December")
_DATE_RE = re.compile(rf"({_MONTHS})-(\d{{1,2}})-(\d{{4}})")


def _parse_date(url: str) -> pd.Timestamp | None:
    m = _DATE_RE.search(url)
    return pd.Timestamp(f"{m.group(1)} {m.group(2)}, {m.group(3)}") if m else None


def load_players() -> pd.DataFrame:
    """Tidy player-match table: date, league, season, match_url (match id),
    team_id, side (h/a, reconstructed from FBref's home-table-first ordering),
    player_id, player, position, minutes, shots, sot, started (True - FBref's
    summary table only lists players who appeared; started/sub isn't captured
    here, unlike Understat, so this is an approximation: treat all as
    potential starters, which is fine for confirmed-XI backtesting)."""
    df = pd.read_json(RAW, lines=True)
    df["date"] = df["match_url"].apply(_parse_date)
    df = df.dropna(subset=["date"])
    for col in ("minutes", "shots", "sot"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["minutes", "shots", "sot"])

    side_map = {}
    for url, g in df.groupby("match_url", sort=False):
        teams = list(dict.fromkeys(g["team_id"]))
        if len(teams) != 2:
            continue  # malformed scrape for this match; drop it
        side_map[(url, teams[0])] = "h"
        side_map[(url, teams[1])] = "a"
    df["side"] = df.apply(lambda r: side_map.get((r["match_url"], r["team_id"])), axis=1)
    df = df.dropna(subset=["side"])
    return df.rename(columns={"match_url": "match_id", "team_id": "team_us"}).reset_index(drop=True)
