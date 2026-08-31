# Theme Switch & Notification Bell Redesign

## Overview

Two related redesigns to the dashboard header's control cluster:

1. **ThemeToggle** goes from a 3-way Light/Dark/System segmented pill to a plain binary Light/Dark sliding switch. "System" is removed entirely, not just hidden.
2. **SubscribeButton** goes from inline text/button states to a compact bell + info icon pair: icons only by default, the bell glows subtly when notifications are on, and tapping the info icon reveals state-specific description text in a floating popover instead of always-visible text.

The bell+info row is repositioned to sit directly above the theme switch (both right-aligned, stacked), replacing the current side-by-side arrangement — confirmed via mockup during brainstorming.

## Architecture

Both components stay self-contained client components with no shared state between them (unchanged from today) — `ThemeToggle` owns the `theme` localStorage key and the `dark` class on `<html>`; `SubscribeButton` owns its own push-subscription status and a small local "popover open" boolean. The pre-hydration flash-prevention script in `layout.tsx` needs a small update to match ThemeToggle's simplified resolution logic, but keeps the same job (apply the right class before hydration, no flash).

## ThemeToggle: binary switch

**Preference model:** `localStorage["theme"]` is now strictly `"light" | "dark"`. There is no `"system"` value and no "absent means follow system" behavior going forward.

**One-time migration:** On mount, if the stored value is anything other than exactly `"light"` or `"dark"` (this covers both a genuinely absent key on a first-ever visit, and a legacy `"system"` value — or literally any other stale garbage — left over from before this change), resolve it once via `window.matchMedia("(prefers-color-scheme: dark)")` and immediately write that resolved value back to `localStorage`. From that point on, the stored value is always a valid `"light"`/`"dark"`, and this migration branch never runs again for that visitor.

**Removed entirely:** the live `matchMedia` "change" event listener that kept the page in sync with OS theme changes while "System" was selected — there's no more "follow system" mode to keep in sync, so this whole effect (and its cleanup) is deleted, not just disabled.

**UI:** a single sliding track-and-knob switch (not a segmented pill) — a sun icon when light is active, a moon icon when dark is active, in the knob. Clicking anywhere on the track toggles between the two states, applies the `dark` class immediately, and persists the new value.

**Flash-prevention script (`layout.tsx`):** keeps resolving "stored valid value, else matchMedia" for the very first paint — same shape as before, just without an ongoing "system" concept baked into it. It doesn't need to write to `localStorage` itself; the component's mount effect handles persisting the migrated value, matching the existing pattern established for the React-Strict-Mode remount fix in the previous round.

## SubscribeButton: bell + info icon pair

**Layout:** two small round icon buttons side by side — bell first, then the info icon — with no visible text in any state by default.

**Bell button (the actual subscribe/unsubscribe action):**
- `checking`: cluster renders nothing at all (unchanged from today).
- `unsupported` / `denied`: bell renders muted grey and non-interactive (no click handler) — matches today's reality that no action is available in these states.
- `off`: bell renders muted grey, clickable — tapping calls the existing `subscribe()` flow.
- `on`: bell renders with a subtle breathing glow (soft indigo halo, ease-in-out, ~2.8s loop — confirmed via mockup), clickable — tapping calls the existing `unsubscribe()` flow.
- `working`: bell keeps its current (pre-transition) visual state but is disabled and shown at reduced opacity while the async subscribe/unsubscribe call is in flight.

**Info button:** always tappable whenever the cluster is rendered at all (i.e. in every state except `checking`). Tapping it toggles a small floating popover open/closed, positioned below the icon row via absolute positioning (doesn't reflow any other page content). The popover closes on a second tap of the info icon, or on a click anywhere else on the page (a document-level click listener, added only while the popover is open and removed when it closes or the component unmounts).

**Popover text per state** (reusing today's exact copy, just moved from always-visible into the popover):
- `unsupported`: "Push notifications aren't supported in this browser. On iPhone, add this page to your Home Screen first, then reopen it from there."
- `denied`: "Notifications blocked. Enable them for this site in your browser settings to get alerts."
- `off`: "Get notified when new picks are logged. Tap the bell to enable."
- `on`: "Notifications on — you'll get alerts when new picks are logged. Tap the bell to turn off."

## Header placement

In `dashboard/app/page.tsx`, the header's inner control group changes from a horizontal row (`ThemeToggle` then `SubscribeButton` side by side) to a vertical stack, right-aligned: the bell+info row on top, the theme switch directly below it. This sits inside the same outer responsive header wrapper from the prior "mobile view fixes" round (`flex-col sm:flex-row` on the header itself) — only the inner group's own arrangement changes, not the outer stacking behavior.

## Error Handling

- `localStorage` unavailable (private browsing, disabled storage): both the flash-prevention script and `ThemeToggle`'s read/write paths keep their existing `try/catch` guards — degrades to a session-only theme (still works for the current page load, just doesn't persist), never throws.
- `matchMedia` unavailable: guarded with a `typeof` check as today; the one-time migration falls back to resolving as light.
- Popover outside-click listener: added/removed defensively (only attached while open) so it can never leak a document-level listener after the component unmounts or the popover closes.

## Testing

No frontend test suite exists in this repo (established in prior rounds) — verification is `tsc --noEmit` + `next build`, plus a manual dev-server pass:
- Toggle Light/Dark and confirm it persists across a reload, with no flash and no hydration warnings.
- Manually seed `localStorage.theme` with `"system"` (and separately, remove the key entirely) and confirm each resolves once on next load and stays fixed as a plain `"light"`/`"dark"` value afterward — the migration branch shouldn't re-trigger on a subsequent reload.
- Force each of the 4 real `SubscribeButton` states (`unsupported`, `denied`, `off`, `on`) and confirm: correct bell appearance (muted/interactive/glowing as specified), correct popover text on tapping info, popover closes on a second info tap and on an outside click.
- Confirm the glow animation only plays in the `on` state, and reads as subtle (matches the approved mockup), not a bright pulse.
- Confirm the bell+info row renders above the switch in the header, right-aligned, and the outer header's existing mobile-stacking behavior is unaffected.
