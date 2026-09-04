"""Pre-lineup "players to watch" for the dashboard's Player props previews.

Confirmed-XI prop rows only exist ~20-40 min before kickoff. Between matchdays
the Props tab still shows the next fixtures as previews; this module ranks
each team's recent non-GK starters by the same shots model the live engine
uses (P(shots 1+) vs this opponent, 85 assumed minutes) so a preview can
expand into a short watchlist without spending API quota on lineups.

Not a substitute for the confirmed-XI table — it's an informed prior from
who has actually been starting.
"""
from __future__ import annotations

import json
from typing import Any, Callable

import pandas as pd

from ..data import PROCESSED_DIR
from ..players import POSITION_GROUPS, LineupModel, load_players
from . import namematch
from .shots_engine import LEAGUE, MINUTES_ASSUMED

WATCHLIST_FILE = PROCESSED_DIR / "upcoming_watchlist.json"
PER_SIDE = 3
LOOKBACK_MATCHES = 6
SHOTS_LINE = 0.5  # P(shots 1+)


def recent_non_gk_starters(
    players: pd.DataFrame,
    league: str,
    team_us: str,
    as_of: pd.Timestamp,
    n_matches: int = LOOKBACK_MATCHES,
) -> list[tuple]:
    """`(player_id, player_name)` for non-GK players who started any of the
    team's last `n_matches` matches before `as_of`. Empty if we have no
    history for the team."""
    hist = players[
        (players["league"] == league)
        & (players["team_us"] == team_us)
        & (players["date"] < as_of)
        & (players["started"])
    ]
    if hist.empty:
        return []
    match_dates = (
        hist[["match_id", "date"]].drop_duplicates("match_id").sort_values("date")
    )
    last_ids = set(match_dates.tail(n_matches)["match_id"])
    recent = hist[hist["match_id"].isin(last_ids)]
    latest = recent.sort_values("date").drop_duplicates("player_id", keep="last")
    out = []
    seen: set = set()
    for row in latest.itertuples(index=False):
        group = POSITION_GROUPS.get(getattr(row, "position", ""), "")
        if group == "GK":
            continue
        pid = row.player_id
        if pid in seen:
            continue
        seen.add(pid)
        out.append((pid, row.player))
    return out


def watch_side(
    model: LineupModel,
    candidates: list[tuple],
    opponent_us: str,
    side: str,
    per_side: int = PER_SIDE,
    predict_fn: Callable | None = None,
) -> list[dict]:
    """Rank `candidates` by P(shots 1+) against `opponent_us`; keep top N."""
    predict = predict_fn or model.predict_player_shots
    scored = []
    for pid, name in candidates:
        try:
            p = float(predict(pid, opponent_us, MINUTES_ASSUMED, SHOTS_LINE, side))
        except Exception:
            continue
        if not pd.notna(p):
            continue
        scored.append({
            "player": name,
            "p_shots_gt0.5": round(p, 3),
        })
    scored.sort(key=lambda r: -r["p_shots_gt0.5"])
    return scored[:per_side]


def watchlist_for_fixture(
    fx: dict,
    players: pd.DataFrame,
    model: LineupModel,
    league: str = LEAGUE,
    per_side: int = PER_SIDE,
    predict_fn: Callable | None = None,
) -> dict[str, Any] | None:
    """One dashboard record, or None if we can't map both team names."""
    names = namematch.team_name_index(players, league)
    home_us = namematch.match_team(str(fx["home"]), names)
    away_us = namematch.match_team(str(fx["away"]), names)
    if not home_us or not away_us:
        return None
    try:
        as_of = pd.Timestamp(fx["kickoff"]).tz_localize(None).normalize()
    except (TypeError, ValueError):
        as_of = pd.Timestamp.now().normalize()
    home_cands = recent_non_gk_starters(players, league, home_us, as_of)
    away_cands = recent_non_gk_starters(players, league, away_us, as_of)
    return {
        "fixture_id": fx["fixture_id"],
        "home": fx["home"],
        "away": fx["away"],
        "kickoff": fx["kickoff"],
        "home_watch": watch_side(model, home_cands, away_us, "h", per_side, predict_fn),
        "away_watch": watch_side(model, away_cands, home_us, "a", per_side, predict_fn),
    }


def build_watchlist(
    upcoming: list[dict],
    players: pd.DataFrame | None = None,
    model: LineupModel | None = None,
    league: str = LEAGUE,
) -> list[dict]:
    if not upcoming:
        return []
    if players is None:
        players = load_players()
    if model is None:
        as_of = pd.Timestamp.now().normalize()
        model = LineupModel.fit(players, league, as_of)
    rows = []
    for fx in upcoming:
        rec = watchlist_for_fixture(fx, players, model, league)
        if rec is None:
            continue
        if not rec["home_watch"] and not rec["away_watch"]:
            continue
        rows.append(rec)
    return rows


def write_watchlist(upcoming: list[dict], path=None) -> list[dict]:
    """Fit once, write `upcoming_watchlist.json`. Isolated so a model/data
    failure never blocks the upcoming-fixtures file itself."""
    dest = path if path is not None else WATCHLIST_FILE
    rows = build_watchlist(upcoming)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"fixtures": rows}, indent=2))
    print(f"watchlist: {len(rows)} fixture(s) -> {dest}")
    return rows
