# Richer Push Notification Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the footymodel push notification's "Goals: ..." line show the model's actual P(O2.5) and expected total goals for the most notable new prediction, instead of a bare list of team names.

**Architecture:** Extract the existing inline goals-summary logic in `scripts/notify_dashboard.py`'s `main()` into a small, directly-testable function, `build_goals_line(goals)`, that picks the most confident new prediction (largest distance from 50%) and formats it with its P(O2.5)/xG numbers, tallying any additional fixtures.

**Tech Stack:** Python 3.11, plain `assert`-based test scripts (matching this project's existing convention — no pytest anywhere in this repo).

See spec: `docs/superpowers/specs/2026-09-01-richer-notification-content-design.md`

---

### Task 1: Extract and enrich `build_goals_line()`

**Files:**
- Modify: `scripts/notify_dashboard.py`
- Create: `scripts/notify_dashboard_test.py`

- [ ] **Step 1: Write the test first**

Create `scripts/notify_dashboard_test.py`:

```python
"""Unit-check for notify_dashboard.py's build_goals_line(): confirms the
featured-fixture selection (the new prediction with the model's most
confident call - largest distance from a 50/50 split) and the one-fixture
vs multi-fixture body format. Pure/data-free - synthetic row dicts only, no
git diff or network involved, safe to run in CI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from notify_dashboard import build_goals_line

# --- one fixture ---
one = [{"home": "Chelsea", "away": "Brighton", "model_p_over25": "0.439", "exp_total_goals": "2.43"}]
line = build_goals_line(one)
print(line)
assert line == "Chelsea v Brighton: 44% O2.5, xG 2.43", line

# --- multiple fixtures: the one furthest from 50% should be featured, not
# just the first in the list (Sunderland v Fulham at 0.360 is 14 points
# from 50%, more than Chelsea's 6.1 or Leeds' 5.2). ---
many = [
    {"home": "Leeds", "away": "Brentford", "model_p_over25": "0.552", "exp_total_goals": "2.89"},
    {"home": "Chelsea", "away": "Brighton", "model_p_over25": "0.439", "exp_total_goals": "2.43"},
    {"home": "Sunderland", "away": "Fulham", "model_p_over25": "0.360", "exp_total_goals": "2.14"},
]
line2 = build_goals_line(many)
print(line2)
assert line2 == "Sunderland v Fulham: 36% O2.5, xG 2.14 (+2 more)", (
    f"expected the fixture furthest from 50% (Sunderland v Fulham) to be featured, got: {line2}"
)

print("ALL CHECKS PASSED — featured-fixture selection and body format are correct.")
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python scripts/notify_dashboard_test.py`
Expected: `ImportError: cannot import name 'build_goals_line' from 'notify_dashboard'` (the function doesn't exist yet).

- [ ] **Step 3: Implement `build_goals_line()` and use it in `main()`**

In `scripts/notify_dashboard.py`, find:

```python
def main() -> None:
```

Replace with:

```python
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
```

Then find, inside `main()`:

```python
    parts = []
    if goals:
        names = [f"{r['home']} v {r['away']}" for r in goals[:3]]
        more = f" +{len(goals) - 3} more" if len(goals) > 3 else ""
        parts.append(f"Goals: {', '.join(names)}{more}")
    if prop_fixtures:
        parts.append(f"Props: {len(prop_fixtures)} fixture(s), {len(props)} player line(s)")
```

Replace with:

```python
    parts = []
    if goals:
        parts.append(build_goals_line(goals))
    if prop_fixtures:
        parts.append(f"Props: {len(prop_fixtures)} fixture(s), {len(props)} player line(s)")
```

- [ ] **Step 4: Run the test again and confirm it passes**

Run: `python scripts/notify_dashboard_test.py`
Expected: ends with `ALL CHECKS PASSED — featured-fixture selection and body format are correct.`

- [ ] **Step 5: Sanity-check the unchanged paths still work**

Run: `python -c "import sys; sys.path.insert(0, 'scripts'); import notify_dashboard"`
Expected: no errors (confirms the module still imports cleanly — `main()`'s git-diff/HTTP-POST logic isn't exercised by the unit test above, so this just confirms nothing else in the file broke syntactically).

- [ ] **Step 6: Commit**

```bash
git add scripts/notify_dashboard.py scripts/notify_dashboard_test.py
git commit -m "feat: include P(O2.5)/xG in push notification content"
```

---

### Task 2: Wire the new test into CI

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add the CI step**

In `.github/workflows/ci.yml`, find:

```yaml
      - name: Missed-fixture backfill script recovery + idempotency (mocked API)
        run: python scripts/backfill_missed_fixtures_test.py
```

Replace with:

```yaml
      - name: Missed-fixture backfill script recovery + idempotency (mocked API)
        run: python scripts/backfill_missed_fixtures_test.py
      - name: Push notification content - featured-fixture selection (pure, data-free)
        run: python scripts/notify_dashboard_test.py
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: wire notify_dashboard_test.py into CI"
```

---

## Post-plan verification

The real notification content will only be observable the next time `live_poll.yml` actually logs a new goals prediction (matches a lineup confirmation, not something to force manually) — no separate manual verification step is needed beyond the unit test, since `main()`'s git-diff-reading and HTTP-POST logic are both unchanged, only the string this one function builds is different.
