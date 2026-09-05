#!/usr/bin/env python3
"""Data-free checks for dashboard fixture timeline bucketing."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS = r"""
import {
  buildFixtureTimeline,
  classifyFixture,
  isFixtureLive,
  todayDateKey,
} from "./dashboard/lib/fixtureTimeline.ts";

const now = Date.parse("2026-09-05T12:00:00.000Z");
const calendar = [
  { fixtureId: "past1", home: "A", away: "B", kickoff: "2026-09-04T15:00:00+00:00" },
  { fixtureId: "today1", home: "C", away: "D", kickoff: "2026-09-05T18:00:00+00:00" },
  { fixtureId: "today2", home: "E", away: "F", kickoff: "2026-09-05T20:00:00+00:00" },
  { fixtureId: "live1", home: "Live", away: "Now", kickoff: "2026-09-05T11:00:00+00:00" },
  { fixtureId: "prev1", home: "G", away: "H", kickoff: "2026-09-06T14:00:00+00:00" },
  { fixtureId: "prev2", home: "I", away: "J", kickoff: "2026-09-07T14:00:00+00:00" },
  { fixtureId: "prev3", home: "K", away: "L", kickoff: "2026-09-08T14:00:00+00:00" },
  { fixtureId: "prev4", home: "M", away: "N", kickoff: "2026-09-09T14:00:00+00:00" },
  { fixtureId: "prev5", home: "O", away: "P", kickoff: "2026-09-10T14:00:00+00:00" },
  { fixtureId: "prev6", home: "Q", away: "R", kickoff: "2026-09-11T14:00:00+00:00" },
];
const logged = [
  { fixtureId: "past_logged", home: "Old", away: "Side", kickoff: "2026-09-03T15:00:00+00:00" },
];

if (todayDateKey(now) !== "2026-09-05") throw new Error("todayDateKey");
if (classifyFixture("2026-09-04T15:00:00+00:00", now) !== "past") throw new Error("past");
if (classifyFixture("2026-09-05T18:00:00+00:00", now) !== "today") throw new Error("today");
if (classifyFixture("2026-09-06T14:00:00+00:00", now) !== "preview") throw new Error("preview");

const liveFixture = { fixtureId: "live1", home: "Live", away: "Now", kickoff: "2026-09-05T11:00:00+00:00" };
if (classifyFixture(liveFixture.kickoff, now, new Set(), liveFixture) !== "today") {
  throw new Error("in-progress stays today");
}
if (!isFixtureLive(liveFixture.kickoff, now, new Set(), liveFixture)) {
  throw new Error("in-progress is live");
}

const finishedToday = Date.parse("2026-09-05T16:00:00.000Z");
if (classifyFixture(liveFixture.kickoff, finishedToday, new Set(), liveFixture) !== "past") {
  throw new Error("finished today moves past");
}

const gradedKeys = new Set(["live1"]);
if (classifyFixture(liveFixture.kickoff, now, gradedKeys, liveFixture) !== "past") {
  throw new Error("graded moves past");
}

const tl = buildFixtureTimeline(calendar, logged, 5, now);
if (tl.today.length !== 3) throw new Error(`today ${tl.today.length}`);
if (tl.today[0].fixtureId !== "live1") throw new Error("live sorts first");
if (tl.preview.length !== 5) throw new Error(`preview ${tl.preview.length}`);
if (tl.preview[0].fixtureId !== "prev1") throw new Error("preview order");
if (!tl.past.some((f) => f.fixtureId === "past_logged")) throw new Error("logged past missing");

import { sortPastByKickoff } from "./dashboard/lib/fixtureTimeline.ts";
const pastSorted = sortPastByKickoff([
  { kickoff: "2026-09-01T15:00:00+00:00" },
  { kickoff: "2026-09-03T15:00:00+00:00" },
  { kickoff: "2026-09-02T15:00:00+00:00" },
]);
if (pastSorted[0].kickoff !== "2026-09-03T15:00:00+00:00") throw new Error("past sort desc");

console.log("dashboard_timeline_test: OK");
"""

proc = subprocess.run(
    ["npx", "tsx", "-e", TS],
    cwd=ROOT,
    capture_output=True,
    text=True,
)
if proc.returncode != 0:
    print(proc.stdout)
    print(proc.stderr, file=sys.stderr)
    sys.exit(proc.returncode)
print(proc.stdout.strip())
