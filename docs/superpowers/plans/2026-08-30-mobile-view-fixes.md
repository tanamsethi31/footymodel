# Mobile View Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two reproducible mobile-viewport bugs on the footymodel dashboard: the page header overflowing horizontally (making the whole page scroll sideways), and the tab bar's animated active-tab highlight losing track of the selected tab once the 5-tab pill bar needs to scroll.

**Architecture:** Both fixes are small, targeted changes to existing files — a responsive Tailwind class change on the header (Task 1), and one added line plus empirical verification in the tab bar's existing scroll-position effect (Task 2). No new files, no new dependencies.

**Tech Stack:** Next.js App Router, TypeScript, Tailwind CSS v4 (`dashboard/`).

See spec: `docs/superpowers/specs/2026-08-30-mobile-view-fixes-design.md`

---

### Task 1: Header stacks vertically below the `sm` breakpoint

**Files:**
- Modify: `dashboard/app/page.tsx`

- [ ] **Step 1: Make the header responsive**

In `dashboard/app/page.tsx`, find:

```tsx
      <header className="flex items-start justify-between gap-4 mb-10">
```

Replace with:

```tsx
      <header className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-10">
```

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors (pure className change).

- [ ] **Step 3: Manually verify at mobile width**

Run: `cd dashboard && npm run dev`, open `http://localhost:3000` in a browser with devtools open, and emulate a 375px-wide mobile viewport (devtools device toolbar, or resize the window narrow).

Run this in the devtools console to confirm the page no longer overflows horizontally:

```js
document.documentElement.scrollWidth <= document.documentElement.clientWidth
```

Expected: `true`. Also visually confirm the logo/description block renders first, with the Light/Dark/System toggle and Subscribe button (or the "Notifications blocked..." text, whichever is currently showing) rendering as their own full-width row directly below it, not cut off or overlapping anything.

Then widen the viewport back past 640px (the Tailwind `sm` breakpoint) and confirm the header returns to its original side-by-side layout, unchanged from before this task.

Stop the dev server (`Ctrl+C`) when done.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/page.tsx
git commit -m "fix: stack header vertically on mobile to prevent horizontal overflow"
```

---

### Task 2: Tab bar scrolls the active tab into view

**Files:**
- Modify: `dashboard/components/DashboardTabs.tsx`

- [ ] **Step 1: Scroll the newly-active tab into view**

In `dashboard/components/DashboardTabs.tsx`, find:

```tsx
  useLayoutEffect(() => {
    const wrapper = wrapperRef.current;
    const btn = buttonRefs.current[active];
    if (!wrapper || !btn) return;
    // Measure against the buttons wrapper, not the (fixed-frame) scroll
    // container - the wrapper and the clip-path overlay are both scrolled
    // content, so their coordinate origins shift together when the tab bar
    // is scrolled. Measuring against the container instead was off by
    // exactly scrollLeft whenever the bar was scrolled off zero.
    const wrapperRect = wrapper.getBoundingClientRect();
    const btnRect = btn.getBoundingClientRect();
    setClip({
      left: btnRect.left - wrapperRect.left,
      right: wrapperRect.right - btnRect.right,
    });
  }, [active]);
```

Replace with:

```tsx
  useLayoutEffect(() => {
    const wrapper = wrapperRef.current;
    const btn = buttonRefs.current[active];
    if (!wrapper || !btn) return;
    // Measure against the buttons wrapper, not the (fixed-frame) scroll
    // container - the wrapper and the clip-path overlay are both scrolled
    // content, so their coordinate origins shift together when the tab bar
    // is scrolled. Measuring against the container instead was off by
    // exactly scrollLeft whenever the bar was scrolled off zero.
    const wrapperRect = wrapper.getBoundingClientRect();
    const btnRect = btn.getBoundingClientRect();
    setClip({
      left: btnRect.left - wrapperRect.left,
      right: wrapperRect.right - btnRect.right,
    });
    // The tab bar itself scrolls horizontally when there isn't room for all
    // 5 tabs (see the container's overflow-x-auto below) - without this,
    // clicking a tab outside the currently-visible scroll window left the
    // container's scroll position unchanged, so the highlight (and the
    // clicked tab's label) could end up entirely off-screen. "nearest" on
    // both axes means this only scrolls the minimum needed, and only
    // horizontally within this tab bar - never the page itself vertically.
    btn.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [active]);
```

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manually verify at mobile width**

Run: `cd dashboard && npm run dev`, open `http://localhost:3000`, emulate a 375px-wide mobile viewport.

Click through all 5 tabs in order (Track record → Goals O/U → Player props → Staking → Glossary) and confirm, for each one:
- The tab bar scrolls (if needed) so the clicked tab's full label is visible.
- The blue highlight visually covers exactly the clicked tab's label — not the previous one, not a partial overlap between two labels.

Then click back through in reverse order (Glossary → Track record) and confirm the same thing holds in both directions.

**If the highlight is still misaligned after this change** (i.e. `scrollIntoView` alone doesn't fix it), that means the clip calculation itself needs to run again after the scroll settles. In that case, wrap the `scrollIntoView` call and a re-measurement in a `requestAnimationFrame`:

```tsx
    btn.scrollIntoView({ block: "nearest", inline: "nearest" });
    requestAnimationFrame(() => {
      const wrapperRect2 = wrapper.getBoundingClientRect();
      const btnRect2 = btn.getBoundingClientRect();
      setClip({
        left: btnRect2.left - wrapperRect2.left,
        right: wrapperRect2.right - btnRect2.right,
      });
    });
```

Only add this fallback if the plain `scrollIntoView` call doesn't fully fix the misalignment when tested — don't add it speculatively.

Also confirm desktop width (≥ 640px, where all 5 tabs already fit with no scrolling) still looks and behaves exactly as before this change.

Stop the dev server (`Ctrl+C`) when done.

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/DashboardTabs.tsx
git commit -m "fix: scroll the active tab into view in the tab bar"
```

---

## Post-plan verification

Once pushed to `origin/main`, confirm live in production (footymodel.vercel.app) at a real mobile viewport width that the page no longer scrolls horizontally, and that tapping through all 5 tabs keeps the highlight correctly aligned with the tapped tab.
