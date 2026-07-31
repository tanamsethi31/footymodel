"""Summarize live paper-trade performance so far - run this whenever you want
a "how's it going" answer mid-season instead of eyeballing raw CSV rows.

Goals/O-U recommendations ARE graded here: final scores are re-fetched from
API-Football by date (cheap - one call per distinct past kickoff date, not
per fixture) and matched back to each logged fixture_id.

Player-prop rows are NOT graded here: that needs actual match shots/SOT
stats, which only exist once WhoScored/FBref/Understat are re-scraped after
the fact (Phase D-G's data sources) - a manual step, not something this
script can fetch automatically. It reports what's been flagged and leaves
grading for whenever that re-scrape happens.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from footymodel.live.client import ApiFootballClient, ApiFootballError
from footymodel.live.engine import LIVE_LOG
from footymodel.live.shots_engine import PROPS_LOG


def _grade_goals(df: pd.DataFrame, client: ApiFootballClient) -> pd.DataFrame:
    df = df.copy()
    df["kickoff_date"] = pd.to_datetime(df["kickoff"]).dt.strftime("%Y-%m-%d")
    scores: dict[int, tuple[int, int]] = {}
    for date_str in sorted(df["kickoff_date"].unique()):
        try:
            fixtures = client.fixtures_by_date(date_str)
        except ApiFootballError as e:
            print(f"  ! couldn't fetch results for {date_str}: {e}")
            continue
        for fx in fixtures:
            if fx["fixture"]["status"]["short"] == "FT":
                scores[fx["fixture"]["id"]] = (fx["goals"]["home"], fx["goals"]["away"])

    def _profit(row):
        s = scores.get(row["fixture_id"])
        if s is None:
            return None  # not finished yet, or result unavailable
        over_hit = (s[0] + s[1]) > 2.5
        # Bet whichever side was logged as +EV; None if neither was (no bet placed).
        if row.get("ev_over25", -1) > 0 and pd.notna(row.get("odds_over25")):
            return row["odds_over25"] - 1 if over_hit else -1.0
        if row.get("ev_under25", -1) > 0 and pd.notna(row.get("odds_under25")):
            return row["odds_under25"] - 1 if not over_hit else -1.0
        return None

    df["profit"] = df.apply(_profit, axis=1)
    return df


def main():
    if LIVE_LOG.exists():
        goals = pd.read_csv(LIVE_LOG)
        goals = _grade_goals(goals, ApiFootballClient())
        settled = goals.dropna(subset=["profit"])
        print(f"=== Goals/O-U: {len(goals)} logged, {len(settled)} settled bets ===")
        if len(settled):
            yield_pct = 100 * settled["profit"].sum() / len(settled)
            print(f"  yield so far: {yield_pct:+.1f}%  (n={len(settled)} bets)")
        cols = ["kickoff", "home", "away", "model_p_over25", "odds_over25",
               "odds_under25", "ev_over25", "ev_under25", "profit"]
        print(goals[cols].to_string(index=False))
    else:
        print("No goals recommendations logged yet.")

    print()
    if PROPS_LOG.exists():
        props = pd.read_csv(PROPS_LOG)
        n_priced = int(props["odds_shots_gt0.5"].notna().sum()) if "odds_shots_gt0.5" in props else 0
        print(f"=== Player props: {len(props)} rows logged ({n_priced} with real odds matched) ===")
        print("NOT graded here - needs actual match shots/SOT stats, only available "
              "once WhoScored/FBref/Understat are re-scraped after the fact (manual).")
    else:
        print("No player-prop rows logged yet.")


if __name__ == "__main__":
    main()
