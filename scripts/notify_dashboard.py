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


def build_props_line(props: list[dict]) -> str:
    """Summarize newly logged player-prop rows for push notifications."""
    by_fixture: dict[str, list[dict]] = {}
    for row in props:
        fid = row.get("fixture_id") or ""
        by_fixture.setdefault(str(fid), []).append(row)

    def fixture_label(rows: list[dict]) -> str:
        home = rows[0].get("home") or "?"
        away = rows[0].get("away") or "?"
        return f"{home} v {away}"

    def top_player(rows: list[dict]) -> tuple[str, float]:
        best_name, best_p = "?", 0.0
        for r in rows:
            for key in ("p_shots_gt0.5", "p_sot_gt0.5"):
                try:
                    p = float(r.get(key) or 0)
                except (TypeError, ValueError):
                    continue
                if p > best_p:
                    best_p, best_name = p, r.get("player") or "?"
        return best_name, best_p

    featured_fid = max(
        by_fixture,
        key=lambda fid: max(
            float(r.get("p_shots_gt0.5") or 0) for r in by_fixture[fid]
        ),
    )
    rows = by_fixture[featured_fid]
    player, prob = top_player(rows)
    line = f"{fixture_label(rows)}: {player} {round(prob * 100)}% shots/SOT lead"
    extra_fixtures = len(by_fixture) - 1
    if extra_fixtures > 0:
        line += f" (+{extra_fixtures} more fixture(s), {len(props)} lines)"
    else:
        line += f" ({len(props)} player lines)"
    return line


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


def build_notification(
    props: list[dict], goals: list[dict]
) -> tuple[str, str] | None:
    """Return (title, body) for a combined matchday push, or None if empty."""
    prop_fixtures = {r["fixture_id"] for r in props if r.get("fixture_id")}
    if not prop_fixtures and not goals:
        return None

    parts: list[str] = []
    if goals:
        try:
            parts.append(build_goals_line(goals))
        except Exception as e:
            print(f"  ! build_goals_line failed, falling back to count: {e}")
            parts.append(f"{len(goals)} goals O/U line(s)")

    if props:
        try:
            parts.append(build_props_line(props))
        except Exception as e:
            print(f"  ! build_props_line failed, falling back to counts: {e}")
            parts.append(f"{len(prop_fixtures)} fixture(s), {len(props)} player line(s)")

    if prop_fixtures and goals:
        title = (
            f"Matchday: {len(prop_fixtures)} props + {len(goals)} goals update(s)"
        )
    elif goals:
        title = f"{len(goals)} new footymodel goals O/U prediction(s)"
    else:
        title = f"{len(prop_fixtures)} new footymodel prop fixture(s)"
    return title, " | ".join(parts)


def main() -> None:
    url = os.environ.get("NOTIFY_URL")
    secret = os.environ.get("NOTIFY_SECRET")
    if not url or not secret:
        print("NOTIFY_URL/NOTIFY_SECRET not set, skipping notification")
        return

    props = _new_rows("data/processed/live_player_props.csv")
    goals = _new_rows("data/processed/live_recommendations.csv")
    built = build_notification(props, goals)
    if built is None:
        print("No new props or goals rows, skipping notification")
        return
    title, body = built

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
