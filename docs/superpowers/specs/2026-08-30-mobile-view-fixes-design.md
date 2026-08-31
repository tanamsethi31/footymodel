# Mobile View Fixes Design

## Overview

Two reproducible visual bugs on the footymodel dashboard, confirmed by testing directly at a 375px (iPhone-size) viewport:

1. The page header overflows horizontally, making the entire page horizontally scrollable on mobile — confirmed via `document.documentElement.scrollWidth` (449px) exceeding `clientWidth` (375px), a 74px overflow.
2. The tab bar's animated blue active-tab indicator visibly lands on the wrong tab once the 5-tab pill bar needs its own horizontal scroll (already an intentional design from earlier work, for when 5 tabs don't fit one screen width) — confirmed by switching to Goals O/U, Player Props, and Staking at mobile width and observing the highlight misaligned each time, worse for tabs further to the right. The container also never scrolls to bring a newly-selected tab into view at all.

Both are layout/rendering bugs, not data bugs, and both are fixed with native CSS/DOM behavior — no new dependencies or components.

## Root Causes

**Bug 1:** `dashboard/app/page.tsx`'s `<header className="flex items-start justify-between gap-4 mb-10">` has two children (the logo/description block, and a `flex items-center gap-3` group holding `ThemeToggle` + `SubscribeButton`) but never wraps (no `flex-wrap`, no responsive stacking). `SubscribeButton`'s "notifications denied" status message is a plain `<p>` with no width constraint; as a flex item it won't shrink below its own minimum content width, so on a narrow viewport the whole un-wrapped header row is forced wider than the screen, and with no other constraint stopping it, the entire page becomes horizontally scrollable.

**Bug 2:** `dashboard/components/DashboardTabs.tsx` computes the active-tab highlight's `clip-path` in a `useLayoutEffect` keyed on `active`, measuring the clicked button's position relative to the tab bar's own inner wrapper (correct, scroll-independent geometry). But nothing ever scrolls the tab bar's `overflow-x-auto` container to bring a newly-active tab into view — so when a tab outside the currently-visible scroll window is clicked, the container stays put and the user can't see whether the highlight actually landed correctly, since the relevant part of the strip is off-screen. This is the primary missing piece; the geometry calculation itself may or may not need a follow-up fix once scrolling correctly happens, to be confirmed during implementation.

## Fixes

### 1. Header: stack vertically below a breakpoint

`dashboard/app/page.tsx`'s `<header>` changes from:

```tsx
<header className="flex items-start justify-between gap-4 mb-10">
```

to:

```tsx
<header className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-10">
```

On mobile (below the `sm:` breakpoint, 640px), the logo/description block renders first, and the `ThemeToggle` + `SubscribeButton` group renders as its own full-width row directly below it. No content is hidden, truncated, or resized — the layout simply uses two rows instead of one when there isn't width for one. At `sm:` and above, behavior is byte-identical to today (a horizontal row with the two groups pushed to opposite ends).

### 2. Tab bar: scroll the active tab into view, verify the highlight

In `dashboard/components/DashboardTabs.tsx`'s existing `useLayoutEffect` (keyed on `active`), after computing `clip`, add a call to scroll the newly-active button into view within its own scrollable ancestor:

```tsx
btn.scrollIntoView({ block: "nearest", inline: "nearest" });
```

This uses `block`/`inline: "nearest"` specifically so it only scrolls horizontally within the tab bar's own `overflow-x-auto` container (never the page itself vertically), and only scrolls the minimum distance needed to bring the button fully into view (no-op if it's already visible).

After this change, verify empirically in the dev server (at mobile width) that the blue highlight correctly tracks the active tab through all 5 tabs, in both directions (clicking forward Track record → Glossary, and backward Glossary → Track record). If the highlight is still misaligned after the scroll-into-view fix lands, the follow-up is to also recompute `clip` after the scroll settles (e.g., re-measure in a `requestAnimationFrame` callback after calling `scrollIntoView`, since a smooth/instant scroll can still shift button positions relative to the wrapper's frame in edge cases) — this is a "verify then patch if needed" step, not a separate designed feature, since the exact JS timing can only be confirmed by observing the real rendered behavior.

## Testing

No frontend test suite exists in this repo (established in prior polish rounds) — verification is `tsc --noEmit` + `next build`, plus a manual dev-server pass at a 375px emulated viewport:
- Confirm `document.documentElement.scrollWidth <= document.documentElement.clientWidth` (no horizontal page overflow) in every tab, in both a state where `SubscribeButton` shows its button (granted permission) and where it shows the "denied" text (the longer content that originally triggered the overflow).
- Click through all 5 tabs in order and confirm the blue highlight visually lands on the clicked tab's label every time, with the tab bar auto-scrolling to keep it fully visible.
- Confirm desktop layout (viewport ≥ 640px) is visually unchanged from before this change.
