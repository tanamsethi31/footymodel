# Light/Dark/System Theme Toggle Design

## Overview

Add an explicit light/dark/system theme toggle to the footymodel dashboard. Today, dark mode is driven entirely by the browser's `prefers-color-scheme` media query via Tailwind's default `dark:` variant behavior — there is no way for a visitor to override their OS setting, and no persisted preference. This adds a 3-state control (Light / Dark / System) that overrides the system preference when set, persists across visits, and requires no new dependency.

## Architecture

Three pieces, each with a single responsibility:

1. **Tailwind variant switch** (`dashboard/app/globals.css`): redefine `dark:` to respond to a `dark` class on `<html>` instead of the media query directly, so both manual override and system-following can coexist.
2. **Flash-prevention script** (`dashboard/app/layout.tsx`): a synchronous inline script in `<head>` that applies the right class before React hydrates, so there's no flash of the wrong theme on load.
3. **Toggle component** (new `dashboard/components/ThemeToggle.tsx`): a client component that reads/writes the preference and mutates the `dark` class directly — no React Context or app-wide provider, since every other component already reacts to the `.dark` class purely through its existing `dark:` Tailwind classes.

No new npm dependency. No changes to any other component's styling — every existing `dark:` class keeps working unchanged, only the trigger mechanism changes.

## Components

### 1. Tailwind variant switch (`dashboard/app/globals.css`)

Add one line near the top of the file (after the `@import "tailwindcss";` line):

```css
@custom-variant dark (&:where(.dark, .dark *));
```

This is Tailwind v4's documented mechanism for switching `dark:` from media-query-driven to class-driven. After this change, `dark:` classes anywhere in the app only activate when `<html>` (or an ancestor) carries a `dark` class — the existing `@media (prefers-color-scheme: dark) { :root { ... } }` block for the `--background`/`--foreground` CSS variables in this same file must also be converted to respond to the class instead, so the two stay in sync:

```css
:root[class~="dark"] {
  --background: #0a0a0a;
  --foreground: #ededed;
}
```

(replacing the existing `@media (prefers-color-scheme: dark) { :root { ... } }` block, which would otherwise keep firing independently of the new class-based mechanism).

### 2. Flash-prevention script (`dashboard/app/layout.tsx`)

An inline `<script>` in the `<head>`, injected as a raw script tag via React's standard mechanism for hardcoded (non-interpolated) inline scripts, runs before hydration. The content below is a fixed, static string with no user-supplied or otherwise dynamic data mixed in, so there's no injection/sanitization concern:

```js
(function () {
  var stored = localStorage.getItem("theme");
  var resolved = stored === "light" || stored === "dark"
    ? stored
    : (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  if (resolved === "dark") document.documentElement.classList.add("dark");
})();
```

`<html>` also gets `suppressHydrationWarning` so React doesn't warn about the class attribute differing between server-render and the client (expected and intentional — that's what this script is for).

### 3. Toggle component (`dashboard/components/ThemeToggle.tsx`)

A client component (`"use client"`) rendered in the page header (`dashboard/app/page.tsx`), next to the existing `SubscribeButton`. Visually, a 3-segment pill reusing the existing segmented-control pattern already established in `MatchPropsTable`'s team/threshold switchers (`bg-neutral-100 dark:bg-neutral-900 border ... rounded-lg` wrapper with per-segment buttons) — no new visual pattern invented.

Behavior:
- On mount, reads `localStorage.getItem("theme")` (defaulting to `"system"` if absent) into local state, to highlight the active segment.
- Clicking "Light" or "Dark": writes that value to `localStorage`, and directly adds/removes the `dark` class on `document.documentElement` to match.
- Clicking "System": removes the `theme` key from `localStorage` (or sets it to `"system"` — see Data Flow below for which), and sets the `dark` class based on the current `matchMedia` result.
- While the active preference is "System", the component subscribes to `window.matchMedia("(prefers-color-scheme: dark)")`'s `change` event, updating the `dark` class live if the OS theme changes while the tab is open. The listener is removed when the preference changes away from "System" or the component unmounts.

## Data Flow

- **Preference storage:** `localStorage["theme"]` is one of `"light"`, `"dark"`, or absent (meaning "system"). There is no explicit stored `"system"` value — "System" is represented by the key simply not being set, which keeps the flash-prevention script (Component 2) and the toggle's read logic (Component 3) both trivially consistent: "no value, or a value that isn't light/dark" always means "resolve via matchMedia."
- **Resolution order (used identically by both the inline script and the toggle component):** read `localStorage.theme` → if it's exactly `"light"` or `"dark"`, that's the resolved theme → otherwise resolve via `matchMedia("(prefers-color-scheme: dark)").matches`.
- **Applying a resolved theme:** always the same single operation — add or remove the `dark` class on `document.documentElement`. Every other component on the dashboard is unaffected code-wise; they already carry `dark:` Tailwind classes that now key off this class instead of the media query.

## Error Handling

- **`localStorage` unavailable** (private browsing modes that throw, or disabled storage): both the inline script and the toggle component wrap their `localStorage` calls in `try/catch`; on failure, behavior falls back to pure system-preference resolution for that page load, and clicking Light/Dark in the toggle simply won't persist across a reload (it still works for the current session via the direct class mutation) — no crash, no console error surfaced to the user.
- **`matchMedia` unavailable** (very old browsers): guarded with a feature check (`typeof window.matchMedia === "function"`); if absent, "System" simply resolves to light (matching the existing pre-toggle default behavior when `prefers-color-scheme` can't be evaluated).

## Testing

No frontend test suite exists in this repo (confirmed in the prior dashboard-polish-round spec) — verification is `tsc --noEmit` + `next build`, plus a manual dev-server pass:
- Cycle through Light / Dark / System and confirm the whole page (not just the toggle itself) restyles correctly in each state.
- Reload the page after picking Light or Dark and confirm the choice persists (no flash of the other theme, no reset to System).
- Reload while set to "System" and toggle the OS/browser's dark mode preference with the tab open; confirm the page updates live without a manual reload.
- Check the browser console for hydration-mismatch warnings after a hard reload in each of the 3 states — there should be none, given `suppressHydrationWarning` on `<html>`.
