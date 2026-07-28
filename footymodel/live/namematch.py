"""Fuzzy name matching: API-Football team/player names -> Understat identities.

Two different sources never agree on spelling ("Man United" vs "Manchester
United", accented vs unaccented names). We match by similarity, scoped as
tightly as possible (player matching is scoped to the mapped team's own roster,
so it's really a ~25-name search, not a global one) to keep this reliable.
"""
from __future__ import annotations

from difflib import SequenceMatcher

# Understat already uses full names ("Manchester City", "Tottenham") that
# fuzzy-match fine against most sources. Only hardcode genuine mismatches
# discovered in practice — verify against live API-Football data once a key
# is available (`python -m footymodel.live.engine --verify-leagues`) and add
# entries here as they surface, rather than guessing upfront.
TEAM_OVERRIDES: dict[str, str] = {}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def best_match(query: str, candidates: list[str], threshold: float = 0.6) -> str | None:
    """Best fuzzy match for `query` among `candidates`, or None if nothing clears
    `threshold`. Checks TEAM_OVERRIDES first for known-tricky names."""
    if query in TEAM_OVERRIDES and TEAM_OVERRIDES[query] in candidates:
        return TEAM_OVERRIDES[query]
    if not candidates:
        return None
    scored = [(c, _similarity(query, c)) for c in candidates]
    scored.sort(key=lambda x: -x[1])
    best, score = scored[0]
    return best if score >= threshold else None


def match_team(api_team_name: str, understat_team_names: list[str]) -> str | None:
    return best_match(api_team_name, understat_team_names, threshold=0.55)


def match_player(api_player_name: str, roster_names: dict) -> int | None:
    """roster_names: {player_name: player_id} for ONE team's known squad.
    Returns the matched player_id, or None if no confident match (caller should
    fall back to the model's average-player rating rather than guessing)."""
    match = best_match(api_player_name, list(roster_names.keys()), threshold=0.6)
    return roster_names.get(match) if match else None


def team_roster_index(players_df, league: str, team_us: str, lookback_days: int = 400) -> dict:
    """Most-recent {player_name: player_id} for one team, for player matching."""
    import pandas as pd
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=lookback_days)
    sub = players_df[(players_df["league"] == league) & (players_df["team_us"] == team_us)
                     & (players_df["date"] >= cutoff)]
    if sub.empty:  # widen if the team has no very recent data
        sub = players_df[(players_df["league"] == league) & (players_df["team_us"] == team_us)]
    # keep each player's most recent name occurrence
    recent = sub.sort_values("date").drop_duplicates("player_id", keep="last")
    return dict(zip(recent["player"], recent["player_id"]))


def team_name_index(players_df, league: str) -> list[str]:
    return sorted(set(players_df[players_df["league"] == league]["team_us"]))
