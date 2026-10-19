#!/usr/bin/env python3
"""Backfill model props + post-match grading for the latest N PL fixtures.

Uses Understat per-match rosters when available (fetch + cache). When
Understat has not published the match yet, builds a proxy XI from each
team's most recent appearance in player_match.parquet so the model still
runs (flagged in graded output).

Writes:
  data/processed/live_player_props.csv      (append new fixture blocks)
  data/processed/graded_props_fixtures.csv
  data/processed/graded_props_players.csv
  data/processed/match_detail.jsonl         (props lineups)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from footymodel.data import PROCESSED_DIR
from footymodel.fbref import SOTModel, load_players as load_fbref_players
from footymodel.live import match_detail, namematch
from footymodel.live.shots_engine import PROPS_LOG, PROPS_LOG_COLUMNS, PropsWatcher
from footymodel.players import LineupModel, load_players as load_understat_players
from footymodel.understat import DIV_TO_UNDERSTAT, RAW_XG_DIR, fetch_match_players

LEAGUE = "E0"
FIXTURES_OUT = PROCESSED_DIR / "graded_props_fixtures.csv"
PLAYERS_OUT = PROCESSED_DIR / "graded_props_players.csv"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _kickoff_day(kickoff: pd.Timestamp) -> pd.Timestamp:
    k = pd.Timestamp(kickoff)
    if k.tzinfo is not None:
        k = k.tz_convert("UTC").tz_localize(None)
    return k.normalize()


def _find_understat_match_id(home: str, away: str, kickoff: pd.Timestamp) -> str | None:
    us = DIV_TO_UNDERSTAT[LEAGUE]
    day = _kickoff_day(kickoff)
    for year in (kickoff.year, kickoff.year - 1):
        cache = RAW_XG_DIR / f"{us}_{year}.json"
        if not cache.exists():
            continue
        payload = json.loads(cache.read_text())
        for d in payload.get("dates", []):
            if not d.get("isResult"):
                continue
            dt = pd.Timestamp(d["datetime"]).normalize()
            if dt != day:
                continue
            h, a = d["h"]["title"], d["a"]["title"]
            if namematch.best_match(home, [h], 0.5) and namematch.best_match(away, [a], 0.5):
                return str(d["id"])
    return None


def _starters_from_understat(match_id: str) -> tuple[list[str], list[str], dict[str, int], dict[str, float]]:
    rows = fetch_match_players(match_id, refresh=False)
    if not rows:
        rows = fetch_match_players(match_id, refresh=True)
    home, away = [], []
    shots: dict[str, int] = {}
    xg: dict[str, float] = {}
    for r in rows:
        if r.get("position") == "Sub":
            continue
        name = r["player"]
        shots[name] = int(r.get("shots", 0))
        xg[name] = float(r.get("xg", 0))
        if r["side"] == "h":
            home.append(name)
        else:
            away.append(name)
    # Keep typical XI size
    return home[:11], away[:11], shots, xg


def _proxy_starters(players: pd.DataFrame, team_us: str, before: pd.Timestamp) -> list[str]:
    before_naive = before.tz_convert("UTC").tz_localize(None) if before.tzinfo else before
    dates = pd.to_datetime(players["date"])
    g = players[(players["league"] == LEAGUE) & (players["team_us"] == team_us) & (dates < before_naive)]
    if g.empty:
        return []
    last = g.sort_values("date").iloc[-1]["match_id"]
    side_rows = g[g["match_id"] == last].sort_values("minutes", ascending=False)
    names = side_rows["player"].tolist()[:11]
    return names


def _sot_from_shots_payload(match_id: str) -> dict[str, int]:
    path = Path(__file__).resolve().parent.parent / "data" / "raw_understat_matches" / f"{match_id}.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    sot: dict[str, int] = {}
    for side in ("h", "a"):
        for shot in payload.get("shots", {}).get(side, []):
            if shot.get("result") in ("Goal", "SavedShot", "ShotOnPost"):
                p = shot.get("player", "")
                sot[p] = sot.get(p, 0) + 1
    return sot


def _hit_over(prob: float | None, actual: int, line: float) -> bool | None:
    if prob is None:
        return None
    return actual > line


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=5, help="Number of recent E0 fixtures")
    args = parser.parse_args()

    matches = pd.read_parquet(PROCESSED_DIR / "matches_xg.parquet")
    e0 = matches[matches["league"] == LEAGUE].sort_values("date", ascending=False).head(args.n)

    understat = load_understat_players()
    fbref = load_fbref_players()
    watcher = PropsWatcher(allow_no_client=True)

    fixture_rows = []
    player_grade_rows = []
    props_to_append = []

    for _, m in e0.iterrows():
        kickoff = pd.Timestamp(m["date"])
        if kickoff.tzinfo is None:
            kickoff = kickoff.tz_localize("UTC")
        if kickoff.hour == 0 and kickoff.minute == 0:
            kickoff = kickoff + pd.Timedelta(hours=15)
        home_fd, away_fd = m["home_team"], m["away_team"]
        fixture_id = f"hist_{_norm(home_fd)}_{_norm(away_fd)}_{kickoff.strftime('%Y%m%d')}"

        us_id = _find_understat_match_id(home_fd, away_fd, kickoff)
        proxy = False
        actual_shots: dict[str, int] = {}
        actual_sot: dict[str, int] = {}
        xg_map: dict[str, float] = {}

        if us_id:
            home_names, away_names, actual_shots, xg_map = _starters_from_understat(us_id)
            actual_sot = _sot_from_shots_payload(us_id)
            fixture_id = f"us_{us_id}"
        else:
            proxy = True
            u_teams = namematch.team_name_index(understat, LEAGUE)
            home_us = namematch.match_team(home_fd, u_teams) or home_fd
            away_us = namematch.match_team(away_fd, u_teams) or away_fd
            home_names = _proxy_starters(understat, home_us, kickoff)
            away_names = _proxy_starters(understat, away_us, kickoff)

        if len(home_names) < 8 or len(away_names) < 8:
            print(f"! skip {home_fd} v {away_fd}: insufficient XI ({len(home_names)}/{len(away_names)})")
            continue

        as_of = kickoff - pd.Timedelta(hours=1)
        if as_of.tzinfo is not None:
            as_of = as_of.tz_convert("UTC").tz_localize(None)
        watcher._shots_model = LineupModel.fit(understat, LEAGUE, as_of)
        watcher._sot_model = SOTModel.fit(fbref, LEAGUE, as_of)

        kickoff_iso = kickoff.isoformat()
        prop_rows = watcher.build_rows_for_starters(
            fixture_id=fixture_id,
            kickoff=kickoff_iso,
            home_name=home_fd,
            away_name=away_fd,
            home_starter_names=home_names,
            away_starter_names=away_names,
        )
        props_to_append.extend(prop_rows)

        match_detail.append_details([
            match_detail.log_props_lineups(fixture_id, home_fd, away_fd, home_names, away_names)
        ])

        for row in prop_rows:
            name = row["player"]
            act_sh = actual_shots.get(name)
            act_sot = actual_sot.get(name, 0) if act_sh is not None else None
            grade = {
                "fixture_id": fixture_id,
                "kickoff": kickoff_iso,
                "home": home_fd,
                "away": away_fd,
                "player": name,
                "team": row["team"],
                "proxy_xi": proxy,
                "actual_shots": act_sh,
                "actual_sot": act_sot,
                "actual_xg": xg_map.get(name),
            }
            for line in (0.5, 1.5, 2.5):
                grade[f"p_shots_gt{line}"] = row.get(f"p_shots_gt{line}")
                if act_sh is not None:
                    grade[f"shots_gt{line}_hit"] = _hit_over(row.get(f"p_shots_gt{line}"), act_sh, line)
            for line in (0.5, 1.5):
                grade[f"p_sot_gt{line}"] = row.get(f"p_sot_gt{line}")
                if act_sot is not None:
                    grade[f"sot_gt{line}_hit"] = _hit_over(row.get(f"p_sot_gt{line}"), act_sot, line)
            player_grade_rows.append(grade)

        n_graded = sum(1 for r in player_grade_rows if r["fixture_id"] == fixture_id and r["actual_shots"] is not None)
        fixture_rows.append({
            "fixture_id": fixture_id,
            "kickoff": kickoff_iso,
            "home": home_fd,
            "away": away_fd,
            "home_goals": int(m["fthg"]),
            "away_goals": int(m["ftag"]),
            "home_shots": int(m["home_shots"]) if pd.notna(m.get("home_shots")) else None,
            "away_shots": int(m["away_shots"]) if pd.notna(m.get("away_shots")) else None,
            "understat_match_id": us_id,
            "proxy_xi": proxy,
            "n_players_graded": n_graded,
            "source": "backfill_understat" if us_id else "backfill_proxy_xi",
        })
        print(f"+ {home_fd} v {away_fd} ({fixture_id}) props={len(prop_rows)} graded_players={n_graded} proxy={proxy}")

    if props_to_append:
        fixture_ids = {r["fixture_id"] for r in props_to_append}
        new_df = pd.DataFrame(props_to_append).reindex(columns=PROPS_LOG_COLUMNS)
        if PROPS_LOG.exists():
            try:
                existing = pd.read_csv(PROPS_LOG, on_bad_lines="skip")
            except TypeError:
                existing = pd.read_csv(PROPS_LOG, error_bad_lines=False)
            if "home" not in existing.columns:
                existing["home"] = ""
                existing["away"] = ""
            existing = existing.reindex(columns=PROPS_LOG_COLUMNS)
            hist_drop = existing["fixture_id"].astype(str).str.startswith("hist_")
            keep = existing[~hist_drop & ~existing["fixture_id"].isin(fixture_ids)]
            out = pd.concat([keep, new_df], ignore_index=True)
        else:
            out = new_df
        out.drop_duplicates(subset=["fixture_id", "player"], keep="last").to_csv(
            PROPS_LOG, index=False
        )

    pd.DataFrame(fixture_rows).to_csv(FIXTURES_OUT, index=False)
    pd.DataFrame(player_grade_rows).to_csv(PLAYERS_OUT, index=False)
    print(f"Wrote {FIXTURES_OUT} ({len(fixture_rows)} fixtures)")
    print(f"Wrote {PLAYERS_OUT} ({len(player_grade_rows)} player rows)")


if __name__ == "__main__":
    main()
