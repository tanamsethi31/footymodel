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
from dataclasses import dataclass, field

import pandas as pd

from .data import ROOT
from .players import DECAY_XI, POSITION_GROUPS, SHOTS_DISPERSION, build_team_xg, _decayed_rate, prob_over

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


def team_display_names(players: pd.DataFrame) -> dict:
    """FBref's team_us is an opaque hex id (from the table's id="stats_XXXX_..."),
    not a name — we never scraped a name field directly. Recover one from the
    match URL slugs: for each team's HOME appearances, the longest common
    prefix across multiple different-opponent slugs isolates the team's own
    name (opponent names vary, so they diverge right after it). FBref's
    "-Derby-" special-named rivalry matches (e.g. "North-London-Derby-...")
    break this and are excluded. Returns {team_us: "Real Name"}."""
    home = players[players["side"] == "h"][["team_us", "match_id"]].drop_duplicates()

    def slug(url: str) -> str:
        tail = url.rstrip("/").split("/")[-1]
        m = _DATE_RE.search(tail)
        return tail[: m.start()] if m else tail

    home = home.assign(slug=home["match_id"].apply(slug))
    home = home[~home["slug"].str.contains("Derby")]

    names = {}
    for tid, g in home.groupby("team_us"):
        slugs = g["slug"].tolist()
        common = slugs[0]
        for s in slugs[1:]:
            i = 0
            while i < min(len(common), len(s)) and common[i] == s[i]:
                i += 1
            common = common[:i]
        names[tid] = common.rstrip("-").replace("-", " ")
    return names


@dataclass
class SOTModel:
    """Shots-on-target rate model — same shrinkage/suppression math already
    confirmed on the Understat shots model (RESULTS.md Phase D: well-calibrated
    from the first pass, gaps within +-0.03). Mirrors LineupModel's
    predict_player_shots() API for consistency.
    """
    league: str
    as_of: pd.Timestamp
    ratings: dict = field(default_factory=dict, repr=False)
    fallback: float = 0.0
    opp_fac: dict = field(default_factory=dict, repr=False)
    venue_fac: dict = field(default_factory=dict, repr=False)
    n_past_matches: int = 0

    @classmethod
    def fit(cls, players: pd.DataFrame, league: str, as_of: pd.Timestamp,
           prior_90s: float = 6.0) -> "SOTModel":
        as_of = pd.Timestamp(as_of)
        past = players[(players["league"] == league) & (players["date"] < as_of)]
        m = cls(league=league, as_of=as_of, n_past_matches=past["match_id"].nunique())
        if past.empty:
            return m

        pos_by_player = (past.groupby("player_id")["position"]
                        .agg(lambda s: s.mode().iat[0])
                        .map(POSITION_GROUPS).fillna("MID"))
        past = past.assign(pos_group=past["player_id"].map(pos_by_player).fillna("MID"))
        m.ratings, m.fallback = _decayed_rate(past, "sot", as_of, DECAY_XI, prior_90s,
                                              group_col="pos_group")
        team_sot = build_team_xg(past, stat_col="sot")
        m.opp_fac = (team_sot.groupby("team")["sot_against"].mean()
                    / team_sot["sot_against"].mean()).to_dict()

        # Home/away venue multiplier - confirmed real (~22% higher home SOT
        # rate league-wide, WhoScored PL 2023/24 walk-forward test). League-
        # wide, not per-team (too noisy at ~19 matches/team/venue).
        side_agg = past.groupby("side").agg(_s=("sot", "sum"), _m=("minutes", "sum"))
        sot_p90 = past["sot"].sum() / (past["minutes"] / 90.0).sum()
        m.venue_fac = ((side_agg["_s"] / (side_agg["_m"] / 90.0)) / sot_p90).to_dict()
        return m

    def predict_player_sot(self, player_id, opponent_team: str,
                           minutes_expected: float, line: float,
                           side: str = "h",
                           dispersion: float | None = SHOTS_DISPERSION) -> float:
        """P(player's shots-on-target in this match > `line`).

        `side`: "h" if this player's team is at home, "a" if away — defaults
        to "h" for backward compatibility, but pass the actual side for live
        predictions."""
        rate = self.ratings.get(player_id, self.fallback)
        rate *= self.opp_fac.get(opponent_team, 1.0)
        rate *= self.venue_fac.get(side, 1.0)
        return prob_over(rate, minutes_expected, line, dispersion)
