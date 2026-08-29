# Dashboard Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the dashboard an icon-first logo, a matching favicon, and one brand accent color (electric blue) applied to the active tab pill — no rename, no layout redesign.

**Architecture:** One new presentational component (`Logo`), one new static favicon file, and two small edits to existing files (swap the header's plain heading for `<Logo />`, recolor the active tab pill). All four pieces share the same icon shape (a circle with a curved trajectory line) and the same blue accent.

**Tech Stack:** Next.js App Router, Tailwind CSS v4 (existing dashboard, no new dependencies).

Full design rationale: `docs/superpowers/specs/2026-08-29-dashboard-rebrand-design.md`.

---

## Task 1: Logo component + favicon

**Files:**
- Create: `dashboard/components/Logo.tsx`
- Create: `dashboard/app/icon.svg`

- [ ] **Step 1: Create the Logo component**

```tsx
export default function Logo() {
  return (
    <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        className="w-6 h-6 shrink-0 text-blue-600 dark:text-blue-400"
        aria-hidden="true"
      >
        <circle cx="9" cy="15" r="4" stroke="currentColor" strokeWidth="1.75" />
        <path
          d="M9 11 C 13 7, 17 9, 21 3"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
        />
      </svg>
      footymodel
    </h1>
  );
}
```

- [ ] **Step 2: Create the favicon**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <circle cx="9" cy="15" r="4" stroke="#2563eb" stroke-width="1.75"/>
  <path d="M9 11 C 13 7, 17 9, 21 3" stroke="#2563eb" stroke-width="1.75" stroke-linecap="round"/>
</svg>
```

`#2563eb` is Tailwind's `blue-600` — same shade as the Logo component's light-mode
icon color, so the browser tab icon matches the in-app logo. Next.js auto-detects
`app/icon.svg` by filesystem convention; no changes needed to `layout.tsx` metadata
or `public/manifest.json`. Leave `dashboard/app/favicon.ico` in place untouched (it
stays as a legacy fallback for browsers that don't support SVG favicons).

- [ ] **Step 3: Type-check**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd dashboard
git add components/Logo.tsx app/icon.svg
git commit -m "Add Logo component and SVG favicon"
```

---

## Task 2: Wire the Logo into the header, recolor the active tab pill

**Files:**
- Modify: `dashboard/app/page.tsx`
- Modify: `dashboard/components/DashboardTabs.tsx`

- [ ] **Step 1: Read both files to confirm their current state**

Run: `cat dashboard/app/page.tsx dashboard/components/DashboardTabs.tsx`

Confirm `page.tsx`'s header still contains:
```tsx
<h1 className="text-2xl font-semibold tracking-tight">footymodel</h1>
```
and `DashboardTabs.tsx`'s active-pill overlay still contains:
```tsx
className="absolute inset-1 flex pointer-events-none bg-white dark:bg-neutral-100 rounded-full transition-[clip-path] duration-[260ms] [transition-timing-function:cubic-bezier(0.23,1,0.32,1)]"
```
and its `<span>` still contains:
```tsx
className="w-32 px-2 py-1.5 rounded-full text-sm font-medium text-neutral-900 whitespace-nowrap text-center"
```
If either differs from this (e.g. from other work landing since this plan was
written), stop and report NEEDS_CONTEXT rather than guessing how to adapt the edit.

- [ ] **Step 2: Swap the header heading for the Logo component**

In `dashboard/app/page.tsx`, add the import (alongside the other component imports
near the top of the file):
```ts
import Logo from "@/components/Logo";
```

Change:
```tsx
          <h1 className="text-2xl font-semibold tracking-tight">footymodel</h1>
```
to:
```tsx
          <Logo />
```

- [ ] **Step 3: Recolor the active tab pill**

In `dashboard/components/DashboardTabs.tsx`, change:
```tsx
            className="absolute inset-1 flex pointer-events-none bg-white dark:bg-neutral-100 rounded-full transition-[clip-path] duration-[260ms] [transition-timing-function:cubic-bezier(0.23,1,0.32,1)]"
```
to:
```tsx
            className="absolute inset-1 flex pointer-events-none bg-blue-600 dark:bg-blue-500 rounded-full transition-[clip-path] duration-[260ms] [transition-timing-function:cubic-bezier(0.23,1,0.32,1)]"
```

And change:
```tsx
                className="w-32 px-2 py-1.5 rounded-full text-sm font-medium text-neutral-900 whitespace-nowrap text-center"
```
to:
```tsx
                className="w-32 px-2 py-1.5 rounded-full text-sm font-medium text-white whitespace-nowrap text-center"
```

Nothing else in either file changes — the `getBoundingClientRect` clip-path
measurement logic, the `w-32` equal button widths, and the transition timing are all
untouched.

- [ ] **Step 4: Type-check**

Run (from `dashboard/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Build**

Run (from `dashboard/`): `npm run build`
Expected: succeeds, no errors.

- [ ] **Step 6: Verify in the browser**

Start the dashboard locally, confirm: the header shows the ball+trajectory icon next
to "footymodel" (blue in both light and dark mode via the OS/browser color-scheme
setting); the browser tab shows the new favicon; clicking through all four tabs shows
a solid blue active pill with white text, correctly aligned under each label (reusing
the existing equal-width/measured-position logic, so this should already work
without further changes — just confirm nothing regressed).

- [ ] **Step 7: Commit**

```bash
cd dashboard
git add app/page.tsx components/DashboardTabs.tsx
git commit -m "Wire Logo into header, recolor active tab pill to the brand accent"
```

- [ ] **Step 8: Push**

```bash
git push origin main
```

Expected: push succeeds; the Vercel auto-deploy (rootDirectory=dashboard, confirmed
working per R046) picks it up automatically.

---

## Plan self-review notes

- **Spec coverage:** Logo component ✓ (Task 1), favicon ✓ (Task 1), header wiring ✓
  (Task 2), active-pill recolor ✓ (Task 2), explicit "nothing else changes" scope
  boundary respected in both tasks (no edits to `MostProbableStrip.tsx`,
  `MatchPropsTable.tsx`, `StakingPanel.tsx`, `TrackRecordPanel`/`GoalsPanel`, or
  `manifest.json`, matching the spec's out-of-scope list).
- **Placeholder scan:** none — every step has complete, runnable code or an exact
  command.
- **Type consistency:** `Logo` is a default export with no props, imported as
  `import Logo from "@/components/Logo"` and used as `<Logo />` — matches between
  Task 1 (where it's defined) and Task 2 (where it's used). The `blue-600`/`blue-400`
  (text) vs `blue-600`/`blue-500` (fill) distinction from the spec is preserved
  exactly: `Logo`'s icon uses `text-blue-600 dark:text-blue-400`, the tab pill's
  *fill* uses `bg-blue-600 dark:bg-blue-500` — these are deliberately different
  shades for a deliberate reason (text-color contrast vs. fill saturation), not a
  typo between the two tasks.
