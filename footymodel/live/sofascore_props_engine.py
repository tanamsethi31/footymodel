"""SofaScore + Playwright player props engine (Option A — free live path).

Runs on a **non-datacenter** machine (self-hosted GitHub Actions runner or a
local match-day cron). GitHub-hosted ubuntu-latest IPs are bot-blocked by
SofaScore; this module is not meant to run there.

Uses confirmed SofaScore lineups and the same shots/SOT models as
shots_engine.py. Book odds are **not** fetched (model-only rows; EV columns
stay empty). No API-Football or RapidAPI quota required.
"""
from __future__ import annotations

import json

import pandas as pd

from ..data import PROCESSED_DIR
from . import fixture_health
from . import match_detail
from .shots_engine import append_props_rows, PropsWatcher
from .sofascore_client import SofaScoreClient, SofaScoreError

# Premier League — same tournament id as sofascore_engine.py
TOURNAMENT_IDS = {
    "E0": 17,
}

DEFAULT_HOURS_AHEAD = 2
# Recover delayed polls that missed the pre-kickoff window (minutes).
LINEUP_LOOKBACK_MINUTES = 180

SEEN_FIXTURES_FILE = PROCESSED_DIR / "sofascore_props_seen_fixtures.json"


def _load_seen() -> set:
    if SEEN_FIXTURES_FILE.exists():
        return set(json.loads(SEEN_FIXTURES_FILE.read_text()))
    return set()


def _save_seen(seen: set) -> None:
    SEEN_FIXTURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FIXTURES_FILE.write_text(json.dumps(sorted(seen)))


class SofaScorePropsWatcher:
    def __init__(self, client: SofaScoreClient):
        self.client = client
        self.props = PropsWatcher(allow_no_client=True)

    def process_event(self, league: str, event: dict) -> list[dict] | None:
        event_id = event["id"]
        home_api = event["homeTeam"]["name"]
        away_api = event["awayTeam"]["name"]
        kickoff = pd.Timestamp(event["startTimestamp"], unit="s", tz="UTC").isoformat()
        fixture_id = f"sofa_{event_id}"

        lineups = self.client.lineups(event_id)
        if not lineups.get("confirmed"):
            return None

        home_names = [
            p["player"]["name"]
            for p in lineups.get("home", {}).get("players", [])
            if p.get("substitute") is False
        ]
        away_names = [
            p["player"]["name"]
            for p in lineups.get("away", {}).get("players", [])
            if p.get("substitute") is False
        ]
        if len(home_names) < 8 or len(away_names) < 8:
            print(f"  ! too few starters ({len(home_names)}/{len(away_names)}) for {home_api} v {away_api}")
            return None

        rows = self.props.build_rows_for_starters(
            fixture_id=fixture_id,
            kickoff=kickoff,
            home_name=home_api,
            away_name=away_api,
            home_starter_names=home_names,
            away_starter_names=away_names,
        )
        if not rows:
            return None

        match_detail.append_details([
            match_detail.log_props_lineups(fixture_id, home_api, away_api, home_names, away_names)
        ])
        return rows

    def run_once(
        self,
        hours_ahead: int = DEFAULT_HOURS_AHEAD,
        lookback_minutes: int = LINEUP_LOOKBACK_MINUTES,
    ) -> list[dict]:
        seen = _load_seen()
        now = pd.Timestamp.now(tz="UTC")
        all_rows: list[dict] = []
        successful_fixture_queries = 0

        dates = sorted({
            now.strftime("%Y-%m-%d"),
            (now + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        })
        for date_str in dates:
            for div, tid in TOURNAMENT_IDS.items():
                try:
                    events = self.client.scheduled_events(tid, date_str)
                except SofaScoreError as e:
                    print(f"! fixtures fetch failed for {div} {date_str}: {e}")
                    continue
                successful_fixture_queries += 1
                for ev in events:
                    status = ev.get("status", {}).get("type")
                    if status not in ("notstarted", "inprogress"):
                        continue
                    eid = ev["id"]
                    if eid in seen:
                        continue
                    kickoff = pd.Timestamp(ev["startTimestamp"], unit="s", tz="UTC")
                    mins_to_ko = (kickoff - now).total_seconds() / 60
                    if not (-lookback_minutes <= mins_to_ko <= hours_ahead * 60):
                        continue
                    print(
                        f"  checking {ev['homeTeam']['name']} v {ev['awayTeam']['name']} "
                        f"(kickoff in {mins_to_ko:.0f}min)"
                    )
                    try:
                        rows = self.process_event(div, ev)
                    except Exception as e:
                        print(f"  ! error processing event {eid}: {e}")
                        fixture_health.record(
                            f"sofa_{eid}",
                            kickoff=kickoff.isoformat(),
                            home=ev["homeTeam"]["name"],
                            away=ev["awayTeam"]["name"],
                            source="sofascore",
                            outcome="lineup_unavailable",
                            detail=str(e),
                        )
                        continue
                    if rows:
                        fixture_health.record(
                            f"sofa_{eid}",
                            kickoff=kickoff.isoformat(),
                            home=ev["homeTeam"]["name"],
                            away=ev["awayTeam"]["name"],
                            source="sofascore",
                            outcome="processed_model_only",
                            detail=f"confirmed lineups; {len(rows)} model-only player-prop row(s)",
                        )
                        all_rows.extend(rows)
                        seen.add(eid)
                    else:
                        fixture_health.record(
                            f"sofa_{eid}",
                            kickoff=kickoff.isoformat(),
                            home=ev["homeTeam"]["name"],
                            away=ev["awayTeam"]["name"],
                            source="sofascore",
                            outcome="lineup_unavailable",
                            detail="SofaScore lineups not confirmed or too few matched starters",
                        )

        if not successful_fixture_queries:
            raise RuntimeError("SofaScore fixture fetch failed for every scheduled date")

        if all_rows:
            n = append_props_rows(all_rows)
            print(f"Logged {n} player-prop rows")
        else:
            print("No new confirmed-lineup fixtures this poll (SofaScore props).")

        _save_seen(seen)
        return all_rows


if __name__ == "__main__":
    import traceback

    print("!" * 72)
    print("PAPER-TRADE / PREDICTION MODE (SofaScore props, model-only).")
    print("!" * 72)
    try:
        with SofaScoreClient() as client:
            SofaScorePropsWatcher(client).run_once()
    except Exception:
        print("!" * 72)
        print("CRON RUN FAILED - nothing was logged this poll. Traceback:")
        print("!" * 72)
        traceback.print_exc()
        raise
