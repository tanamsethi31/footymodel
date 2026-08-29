# Dashboard rebrand: logo, brand identity, accent color — design

Status: approved (R055–R064 in `.ladder/ladder.md`)

## Purpose

Give the dashboard a real visual identity (icon-first logo, one brand accent color,
a proper favicon) without renaming the project or redesigning the existing
cards/tables/layout. Scoped narrowly per the brainstorm: this is identity work, not a
structural redesign.

## Brand decisions (from R055–R063)

- Name stays "footymodel" (R056).
- Tone: serious quant/fintech (R057) — matches the project's actual substance
  (backtested stats, EV, Kelly staking), not a sports-editorial or academic framing.
- Logo: icon-first, wordmark secondary (R058). Icon concept: a minimal circle (the
  ball) with a single curved line arcing away from it, like a shot's expected-goals
  trajectory (R059) — reads as "football" and "prediction" in one shape.
- Accent color: electric blue, added on top of the existing neutral dark base and
  emerald/red EV semantics, neither of which change (R060, R061). Follows the
  codebase's existing `-600` (light mode) / `-400` (dark mode) text-color pairing
  already used for emerald/red; the one place blue needs to work as a *background
  fill* (the active tab pill) uses `-600` light / `-500` dark instead, since a fill
  needs to stay saturated in both themes rather than lightening for text contrast.
- Active tab pill becomes the accent color, replacing the current white/neutral-100
  fill (R063) — ties the brand color directly to the dashboard's core interaction.
- Tab-slide ("always sliding"): no new animation work planned (R062). The pill-slide
  mechanic is already real, continuous motion (`clip-path` transition, 260ms
  cubic-bezier); the alignment bug that made it look broken was fixed in R051, and
  R053's equal-width tabs made the glide distance consistent tab-to-tab. This spec
  reskins the pill's color; if it still doesn't feel "sliding enough" after that visual
  change lands, that's a follow-up decision, not part of this build.

## Components

### `dashboard/components/Logo.tsx` (new)

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

One component, one job: render the icon + wordmark as the page's `<h1>`. Uses
`currentColor` + a Tailwind text-color class so it follows the light/dark theme
automatically, unlike the static favicon below (which can't react to a page's theme
since it renders in the browser chrome, outside any DOM/CSS context).

### `dashboard/app/page.tsx` (modify)

Replace the header's plain heading:
```tsx
<h1 className="text-2xl font-semibold tracking-tight">footymodel</h1>
```
with:
```tsx
<Logo />
```
(new import: `import Logo from "@/components/Logo";`). Nothing else in the header
changes — `SubscribeButton` stays where it is, the description paragraph underneath
stays as-is.

### `dashboard/app/icon.svg` (new)

Next.js App Router auto-detects `app/icon.svg` as the site's favicon/tab icon (no
`layout.tsx` metadata changes needed — this is filesystem-convention-based, same
mechanism that already serves `app/favicon.ico` today, and an SVG icon file takes
precedence when present). Same shape as the `Logo` component's SVG, but with an
explicit color instead of `currentColor` (a standalone favicon has no surrounding
text-color context to inherit from):

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <circle cx="9" cy="15" r="4" stroke="#2563eb" stroke-width="1.75"/>
  <path d="M9 11 C 13 7, 17 9, 21 3" stroke="#2563eb" stroke-width="1.75" stroke-linecap="round"/>
</svg>
```
`#2563eb` is Tailwind's `blue-600` — the same shade used for the icon/text accent in
light mode, so the favicon matches the in-app logo. Transparent background, no fixed
light/dark variant (favicons render in the browser's own chrome, not the page's
theme) — blue-600 is dark/saturated enough to stay legible on both light and dark
browser tab bars.

`app/favicon.ico` (the current default Next.js icon) is left in place as a legacy
fallback for browsers that don't support SVG favicons — not removed, not modified.

### `dashboard/components/DashboardTabs.tsx` (modify)

Only the active-pill fill and its text color change. Currently:
```tsx
className="absolute inset-1 flex pointer-events-none bg-white dark:bg-neutral-100 rounded-full ..."
```
and each `<span>` inside it:
```tsx
className="w-32 px-2 py-1.5 rounded-full text-sm font-medium text-neutral-900 whitespace-nowrap text-center"
```
become:
```tsx
className="absolute inset-1 flex pointer-events-none bg-blue-600 dark:bg-blue-500 rounded-full ..."
```
and:
```tsx
className="w-32 px-2 py-1.5 rounded-full text-sm font-medium text-white whitespace-nowrap text-center"
```
(`text-white` works against both `blue-600` and `blue-500`, so it doesn't need a
`dark:` variant of its own). Nothing else in this file changes — the
`getBoundingClientRect`-based clip-path measurement, the equal `w-32` button widths,
and the 260ms transition timing are all untouched.

## Explicitly out of scope

- No changes to `MostProbableStrip.tsx`, `MatchPropsTable.tsx`, `StakingPanel.tsx`,
  `TrackRecordPanel`/`GoalsPanel` (in `page.tsx`), or any card/table layout.
- No new animation work on the tab-slide itself (see R062's rationale above).
- No PWA icon set (192px/512px PNGs) or `manifest.json` changes — the manifest's
  `icons: []` stays empty; the user asked for a logo and a favicon, not full PWA
  installability, and generating a proper icon set from an SVG is a separate,
  unrequested task.
- No rename, no new domain, no changes outside `dashboard/`.
