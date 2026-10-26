#!/usr/bin/env python3
"""Pre-flight check: calendar, logs, bankroll files, and home-poll nudge state."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from footymodel.live.matchday_status import run_integration_checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory with fixture_calendar.json and live CSV logs",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable lines (name\\tok\\tdetail)",
    )
    args = parser.parse_args()

    report = run_integration_checks(args.processed_dir)
    if args.json:
        for c in report.checks:
            print(f"{c.name}\t{'ok' if c.ok else 'fail'}\t{c.detail}")
    else:
        print("Matchday integration check")
        print("=" * 40)
        for c in report.checks:
            mark = "OK" if c.ok else ("WARN" if not c.critical else "FAIL")
            print(f"[{mark}] {c.name}: {c.detail}")

    if report.ok:
        print("\nAll critical checks passed.")
        return 0
    print("\nOne or more critical checks failed — see above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
