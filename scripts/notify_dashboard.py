"""Called from live_poll.yml right before it commits new prediction rows -
builds a human-readable summary from the staged git diff and POSTs it to
the dashboard's /api/notify route, which fans it out via Web Push to
subscribed phones. No-ops quietly if nothing changed or NOTIFY_URL/
NOTIFY_SECRET aren't set (so this never blocks the actual commit/push).
"""
import csv
import io
import os
import subprocess

import requests


def _new_rows(path: str) -> list[dict]:
    """Newly staged (added) lines in one CSV, parsed against ITS OWN
    header (not the possibly-stale on-disk header - some rows have more
    fields than the original header if new columns were added later, see
    R028/the dashboard's own __parsed_extra handling for why)."""
    diff = subprocess.run(
        ["git", "diff", "--cached", "-U0", "--", path],
        capture_output=True, text=True, check=True,
    ).stdout
    added = [line[1:] for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")]
    if not added:
        return []
    with open(path) as f:
        header = f.readline()
    reader = csv.DictReader(io.StringIO(header + "\n".join(added)))
    return list(reader)


def build_goals_line(goals: list[dict]) -> str:
    """One summary line for the newly-logged goals predictions, featuring
    whichever fixture has the model's most confident call (largest distance
    from a 50/50 split) - a signal every row always has, unlike EV/odds,
    which are only present when a market price happened to be fetched at
    logging time."""
    featured = max(goals, key=lambda r: abs(float(r["model_p_over25"]) - 0.5))
    pct = round(float(featured["model_p_over25"]) * 100)
    exp_goals = float(featured["exp_total_goals"])
    line = f"{featured['home']} v {featured['away']}: {pct}% O2.5, xG {exp_goals:.2f}"
    if len(goals) > 1:
        line += f" (+{len(goals) - 1} more)"
    return line


def main() -> None:
    url = os.environ.get("NOTIFY_URL")
    secret = os.environ.get("NOTIFY_SECRET")
    if not url or not secret:
        print("NOTIFY_URL/NOTIFY_SECRET not set, skipping notification")
        return

    goals = _new_rows("data/processed/live_recommendations.csv")
    props = _new_rows("data/processed/live_player_props.csv")
    prop_fixtures = {r["fixture_id"] for r in props if r.get("fixture_id")}

    if not goals and not prop_fixtures:
        print("No new rows, skipping notification")
        return

    parts = []
    if goals:
        try:
            parts.append(build_goals_line(goals))
        except (ValueError, KeyError) as e:
            # build_goals_line() trusts that model_p_over25/exp_total_goals
            # are always populated - true for every engine today, but this
            # falls back to a plain team-name list rather than crashing (and
            # losing the notification entirely) if that ever isn't the case.
            print(f"  ! build_goals_line failed, falling back to team names: {e}")
            names = [f"{r['home']} v {r['away']}" for r in goals[:3]]
            more = f" +{len(goals) - 3} more" if len(goals) > 3 else ""
            parts.append(f"Goals: {', '.join(names)}{more}")
    if prop_fixtures:
        parts.append(f"Props: {len(prop_fixtures)} fixture(s), {len(props)} player line(s)")

    title = f"{len(goals) + len(prop_fixtures)} new footymodel prediction(s)"
    body = " | ".join(parts)

    try:
        resp = requests.post(
            url,
            headers={"x-notify-secret": secret},
            json={"title": title, "body": body, "url": "/"},
            timeout=15,
        )
        resp.raise_for_status()
        print(f"Notified: {resp.json()}")
    except Exception as e:
        # A failed notification should never fail the poll itself.
        print(f"! notify failed (non-fatal): {e}")


if __name__ == "__main__":
    main()
