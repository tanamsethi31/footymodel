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
