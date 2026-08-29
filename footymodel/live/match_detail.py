"""Shared JSONL side-log for expanded match-detail data (starting XI names,
team-model vs. lineup-model breakdown) that live_recommendations.csv doesn't
carry - see docs/superpowers/specs/2026-08-29-expandable-match-detail-design.md.

Deliberately kept separate from the CSV: live_recommendations.csv's ragged
trailing-column format already caused two bugs this session (R050, R072)
from silently growing optional fields over time. Each line here is a
self-contained JSON object instead, so there's no positional/column-count
ambiguity regardless of which engine writes it.
"""
from __future__ import annotations

import json

from ..data import PROCESSED_DIR

MATCH_DETAIL_LOG = PROCESSED_DIR / "match_detail.jsonl"


def make_detail(fixture_id, home_starters: list[str], away_starters: list[str],
                pred: dict) -> dict:
    """Shape one match's detail row from a LineupModel.predict() result.
    Defined in exactly one place so all three engines log an identical
    schema regardless of their own row-building code."""
    return {
        "fixture_id": fixture_id,
        "home_starters": home_starters,
        "away_starters": away_starters,
        "exp_team": round(pred["exp_team"], 2),
        "exp_full": round(pred["exp_full"], 2),
        "p_over25_team": round(pred["p_over25_team"], 3),
        "p_over25_full": round(pred["p_over25_full"], 3),
    }


def extract_and_log_details(rows: list[dict]) -> None:
    """Pops the private "_detail" key from each row IN PLACE - so it never
    ends up in the live_recommendations.csv DataFrame - and appends the
    collected details to MATCH_DETAIL_LOG as JSONL. Call this AFTER building
    `rows` but BEFORE writing them to the CSV. Never raises: a failure here
    must never look like a lost prediction to the caller, since the actual
    prediction lives entirely in `rows`, independent of this file."""
    details = [r.pop("_detail") for r in rows if "_detail" in r]
    if not details:
        return
    try:
        MATCH_DETAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(MATCH_DETAIL_LOG, "a") as f:
            for d in details:
                f.write(json.dumps(d) + "\n")
    except Exception as e:
        print(f"  ! failed to write match_detail.jsonl (predictions themselves were still logged fine): {e}")
