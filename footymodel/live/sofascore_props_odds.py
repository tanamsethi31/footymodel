"""Parse SofaScore pre-match odds into the same (player, line) maps as shots_engine.

SofaScore's `/event/{id}/odds/{provider}/all` payload varies by match and
bookmaker. Player shots/SOT are not guaranteed (many EPL matches only expose
team markets). This module best-effort extracts per-player N+ lines when present.

When nothing is found, callers should fall back to model-confidence paper stakes
(see paper_props_bankroll.py).
"""
from __future__ import annotations

import re
from fractions import Fraction

from .shots_engine import SHOTS_LINES, SOT_LINES, _lookup_player_odd
from .sofascore_engine import _frac_to_decimal

_PLAYER_LINE_RE = re.compile(r"^(.*)\s*-\s*(\d+)\+$", re.IGNORECASE)
_OVER_LINE_RE = re.compile(r"^over\s+(\d+(?:\.\d+)?)$", re.IGNORECASE)
_LINE_BY_THRESHOLD = {1: 0.5, 2: 1.5, 3: 2.5}


def _line_from_choice_group(choice_group: str | None) -> float | None:
    if not choice_group:
        return None
    cg = str(choice_group).strip()
    try:
        val = float(cg)
        if val in SHOTS_LINES or val in SOT_LINES:
            return val
    except ValueError:
        pass
    m = _OVER_LINE_RE.match(cg)
    if m:
        val = float(m.group(1))
        if val in SHOTS_LINES or val in SOT_LINES:
            return val
    return None


def _is_shots_market(label: str) -> bool:
    low = label.lower()
    if "shot" not in low:
        return False
    if any(x in low for x in ("on target", "on goal", "sot", "shots on")):
        return False
    if any(x in low for x in ("team", "match", "home team", "away team", "total team")):
        return False
    return True


def _is_sot_market(label: str) -> bool:
    low = label.lower()
    return any(x in low for x in ("on target", "on goal", "shots on goal", "sot"))


def _record(best: dict[tuple[str, float], float], player: str, line: float, odd: float) -> None:
    if line not in SHOTS_LINES and line not in SOT_LINES:
        return
    key = (player.strip().lower(), line)
    if key not in best or odd > best[key]:
        best[key] = odd


def parse_sofascore_player_prop_odds(
    markets: list[dict],
) -> tuple[dict[tuple[str, float], float], dict[tuple[str, float], float]]:
    """Return (shots_odds, sot_odds) maps: (player_lower, line) -> decimal odd."""
    shots: dict[tuple[str, float], float] = {}
    sot: dict[tuple[str, float], float] = {}

    for m in markets:
        label = " ".join(
            str(m.get(k) or "")
            for k in ("marketGroup", "marketName", "marketPeriod")
        ).strip()
        shots_market = _is_shots_market(label) if label else False
        sot_market = _is_sot_market(label) if label else False
        line_from_group = _line_from_choice_group(m.get("choiceGroup"))

        for c in m.get("choices", []):
            name = str(c.get("name", "")).strip()
            frac = c.get("fractionalValue")
            if not frac or not name:
                continue
            if name.lower() in {"under", "no", "no goal"}:
                continue
            try:
                odd = _frac_to_decimal(str(frac))
            except (ValueError, ZeroDivisionError):
                continue
            if odd <= 1.0:
                continue

            m_pl = _PLAYER_LINE_RE.match(name)
            if m_pl:
                line = _LINE_BY_THRESHOLD.get(int(m_pl.group(2)))
                player = m_pl.group(1).strip()
                if line is not None:
                    bucket = sot if sot_market else shots
                    _record(bucket, player, line, odd)
                continue

            if not shots_market and not sot_market:
                continue

            target = shots if shots_market else sot
            m_over = _OVER_LINE_RE.match(name)
            if m_over and line_from_group is not None:
                # Player name carried in choiceGroup for some bookmaker layouts.
                player = str(m.get("choiceGroup") or "").strip()
                if player and not _OVER_LINE_RE.match(player):
                    _record(target, player, line_from_group, odd)
                continue

            line = line_from_group
            if line is None:
                continue
            # Player name is the choice label (common SofaScore layout).
            _record(target, name, line, odd)

    return shots, sot


def lookup_shots_odd(shots_odds: dict, player: str, line: float) -> float | None:
    return _lookup_player_odd(shots_odds, player, line)


def lookup_sot_odd(sot_odds: dict, player: str, line: float) -> float | None:
    return _lookup_player_odd(sot_odds, player, line)
