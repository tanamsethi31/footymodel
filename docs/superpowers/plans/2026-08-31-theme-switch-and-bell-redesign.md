# Theme Switch & Notification Bell Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Light/Dark/System segmented pill with a binary Light/Dark switch, and replace the always-visible-text notification UI with a compact bell + info icon pair (glow when on, popover description on tap), positioned above the switch in the header.

**Architecture:** `ThemeToggle.tsx` is rewritten to a 2-value model with a one-time migration for anyone with a stale/absent preference. `SubscribeButton.tsx` is rewritten to render two small icon buttons instead of text/a text button, with a floating popover for the description. A small glow-animation utility is added to `globals.css`. `page.tsx`'s header wiring changes from a horizontal row to a vertical stack (bell+info row above the switch).

**Tech Stack:** Next.js App Router, TypeScript, Tailwind CSS v4 (`dashboard/`).

**Note on `layout.tsx`:** no task touches it. Its existing pre-hydration script already does exactly what the new binary model needs for the first paint — read `localStorage.theme`; if it's exactly `"light"` or `"dark"`, use it; otherwise (a first-ever visit, or a leftover `"system"` value) resolve once via `matchMedia`. That logic doesn't reference `"system"` as an ongoing concept at all, so nothing there needs to change.

See spec: `docs/superpowers/specs/2026-08-31-theme-switch-and-bell-redesign-design.md`

---

### Task 1: Rewrite ThemeToggle as a binary switch

**Files:**
- Modify: `dashboard/components/ThemeToggle.tsx`

- [ ] **Step 1: Replace the whole file**

Replace the entire contents of `dashboard/components/ThemeToggle.tsx` with:

```tsx
"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function systemPrefersDark(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

// Resolves whatever's stored. If it's not exactly "light" or "dark" - a
// first-ever visit with nothing stored, or a leftover "system" value from
// before this switch existed - resolves once via the OS preference instead.
// `migrated` tells the caller whether to persist that resolution so this
// branch never has to run again for this visitor.
function resolvePreference(): { theme: Theme; migrated: boolean } {
  try {
    const stored = localStorage.getItem("theme");
    if (stored === "light" || stored === "dark") {
      return { theme: stored, migrated: false };
    }
  } catch {
    // localStorage unavailable - fall through to a session-only resolution.
  }
  return { theme: systemPrefersDark() ? "dark" : "light", migrated: true };
}

function persist(theme: Theme) {
  try {
    localStorage.setItem("theme", theme);
  } catch {
    // localStorage unavailable (e.g. private browsing) - the theme still
    // applies for this session via the direct class toggle, it just won't
    // persist across a reload.
  }
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  // Correct the default guess to whatever's actually stored (migrating a
  // legacy/missing value once, if needed), right after mount - avoids a
  // server/client render mismatch on the initial paint. Also re-applies the
  // class here, not just React state: Strict Mode's dev-only remount resets
  // <html> to only the attributes in its JSX, stripping whatever class
  // layout.tsx's pre-hydration script added imperatively - without this, a
  // stored preference would flash correctly then flip back on every dev
  // hard-reload (production has no such remount, so this only matters in
  // `npm run dev`).
  useEffect(() => {
    const { theme: resolved, migrated } = resolvePreference();
    setTheme(resolved);
    applyTheme(resolved);
    if (migrated) persist(resolved);
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
    persist(next);
  }

  return (
    <button
      onClick={toggle}
      role="switch"
      aria-checked={theme === "dark"}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      className="relative w-[52px] h-7 rounded-full border border-neutral-200 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-900 transition-colors duration-200"
    >
      <span
        className={`absolute left-0.5 top-0.5 flex items-center justify-center w-6 h-6 rounded-full bg-white dark:bg-neutral-800 shadow-sm text-xs transition-transform duration-200 ${
          theme === "dark" ? "translate-x-6" : "translate-x-0"
        }`}
      >
        {theme === "dark" ? "🌙" : "☀️"}
      </span>
    </button>
  );
}
```

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manually verify in the dev server**

Run: `cd dashboard && npm run dev`, open `http://localhost:3000`.

1. Confirm the header shows a single sliding switch (sun icon on the left/light position, moon icon on the right/dark position) instead of the old 3-segment pill.
2. Click it — confirm the whole page switches theme immediately, the knob slides to the other side, and the icon changes.
3. Reload — confirm the choice persisted.
4. Open devtools, run `localStorage.setItem("theme", "system")` (simulating a visitor who had the old "System" option saved), then reload. Confirm the page renders using your current OS/browser preference, and run `localStorage.getItem("theme")` again afterward — it should now read exactly `"light"` or `"dark"`, not `"system"`, confirming the one-time migration wrote back a real value.
5. Run `localStorage.removeItem("theme")` and reload — confirm this also resolves once via your OS preference and gets persisted as a real value (same migration path, for a first-ever visitor).
6. Check the console for hydration warnings — none expected.

Stop the dev server (`Ctrl+C`) when done.

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/ThemeToggle.tsx
git commit -m "feat: replace Light/Dark/System pill with a binary theme switch"
```

---

### Task 2: Add the bell glow animation to globals.css

**Files:**
- Modify: `dashboard/app/globals.css`

- [ ] **Step 1: Add the keyframes and utility class**

In `dashboard/app/globals.css`, find:

```css
@media (prefers-reduced-motion: reduce) {
  .animate-stagger-in,
  .animate-panel-in {
    animation: none;
    opacity: 1;
    transform: none;
  }
}
```

Replace with:

```css
@keyframes bell-glow {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.25);
  }
  50% {
    box-shadow: 0 0 8px 2px rgba(99, 102, 241, 0.35);
  }
}
.animate-bell-glow {
  animation: bell-glow 2.8s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .animate-stagger-in,
  .animate-panel-in {
    animation: none;
    opacity: 1;
    transform: none;
  }
  .animate-bell-glow {
    animation: none;
  }
}
```

This is the same subtle breathing indigo halo approved during brainstorming (a soft glow that fades in and out, not a bright pulse), and it's added to the same reduced-motion override this file already uses for its other two animations, so visitors with reduced-motion preferences get a static (non-animating) glow-free bell instead.

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors (pure CSS change).

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/globals.css
git commit -m "feat: add bell-glow animation utility"
```

---

### Task 3: Rewrite SubscribeButton as a bell + info icon pair

**Files:**
- Modify: `dashboard/components/SubscribeButton.tsx`

- [ ] **Step 1: Replace the whole file**

Replace the entire contents of `dashboard/components/SubscribeButton.tsx` with:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

type Status = "checking" | "unsupported" | "denied" | "off" | "on" | "working";

const DESCRIPTIONS: Record<Exclude<Status, "checking">, string> = {
  unsupported:
    "Push notifications aren't supported in this browser. On iPhone, add this page to your Home Screen first, then reopen it from there.",
  denied:
    "Notifications blocked. Enable them for this site in your browser settings to get alerts.",
  off: "Get notified when new picks are logged. Tap the bell to enable.",
  on: "Notifications on — you'll get alerts when new picks are logged. Tap the bell to turn off.",
  working: "Working…",
};

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

export default function SubscribeButton() {
  const [status, setStatus] = useState<Status>("checking");
  const [infoOpen, setInfoOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setStatus("unsupported");
      return;
    }
    if (Notification.permission === "denied") {
      setStatus("denied");
      return;
    }
    navigator.serviceWorker.register("/sw.js").then(async (reg) => {
      const existing = await reg.pushManager.getSubscription();
      setStatus(existing ? "on" : "off");
    });
  }, []);

  // Close the popover on a click anywhere outside this component - only
  // attached while it's actually open, removed the moment it closes (or the
  // component unmounts), so this never leaks a document-level listener.
  useEffect(() => {
    if (!infoOpen) return;
    function onDocClick(e: MouseEvent) {
      if (!wrapperRef.current?.contains(e.target as Node)) setInfoOpen(false);
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, [infoOpen]);

  async function subscribe() {
    setStatus("working");
    const reg = await navigator.serviceWorker.ready;
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      setStatus(permission === "denied" ? "denied" : "off");
      return;
    }
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(
        process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY!
      ),
    });
    await fetch("/api/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sub),
    });
    setStatus("on");
  }

  async function unsubscribe() {
    setStatus("working");
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      await fetch("/api/subscribe", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(sub),
      });
      await sub.unsubscribe();
    }
    setStatus("off");
  }

  if (status === "checking") return null;

  const interactive = status === "off" || status === "on";

  function handleBellClick() {
    if (status === "on") unsubscribe();
    else if (status === "off") subscribe();
  }

  return (
    <div ref={wrapperRef} className="relative flex items-center gap-2">
      <button
        onClick={handleBellClick}
        disabled={!interactive}
        aria-label={
          status === "on"
            ? "Notifications on - tap to turn off"
            : status === "off"
              ? "Get notified of new picks"
              : status === "denied"
                ? "Notifications blocked"
                : "Notifications unsupported in this browser"
        }
        className={`w-9 h-9 rounded-full border flex items-center justify-center text-base transition-opacity duration-300 ${
          status === "on"
            ? "border-indigo-800 dark:border-indigo-400 text-indigo-200 animate-bell-glow"
            : "border-neutral-200 dark:border-neutral-800 text-neutral-400 dark:text-neutral-600"
        } ${status === "working" ? "opacity-50" : ""} ${interactive ? "" : "cursor-default"}`}
      >
        {/* During "working", this always shows the muted glyph rather than
            trying to preserve which direction the transition is going -
            it's a brief, sub-second state either way, not worth the extra
            bookkeeping to track the pre-transition glyph. */}
        {status === "on" ? "🔔" : "🔕"}
      </button>
      <button
        onClick={() => setInfoOpen((o) => !o)}
        aria-expanded={infoOpen}
        aria-label="What does this mean?"
        className="w-9 h-9 rounded-full border border-neutral-200 dark:border-neutral-800 flex items-center justify-center text-sm text-neutral-400 dark:text-neutral-600"
      >
        ⓘ
      </button>
      {infoOpen && (
        <div className="absolute top-full right-0 mt-2 w-64 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3 text-xs text-neutral-500 dark:text-neutral-400 shadow-lg z-20">
          {DESCRIPTIONS[status]}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manually verify in the dev server**

Run: `cd dashboard && npm run dev`, open `http://localhost:3000`.

1. Confirm only two small round icons render (bell, then info) — no visible text.
2. Whatever your current browser's notification permission state is, confirm the bell looks right for it: muted/non-interactive if `denied` or unsupported, muted/clickable if `off`, glowing/clickable if `on`.
3. Tap the info icon — confirm a small popover appears below the icons with text matching your current state, and the rest of the page doesn't shift.
4. Tap the info icon again — confirm it closes. Open it again, then click anywhere else on the page — confirm it also closes.
5. If your browser is in the `off` state, click the bell and grant the permission prompt — confirm the bell briefly shows a dimmed/disabled look, then switches to the glowing `on` look once subscribed. Click it again to unsubscribe and confirm it returns to the muted `off` look.
6. Confirm the glow only plays while `on`, and it reads as a slow, subtle breathing halo, not a bright pulse.

Stop the dev server (`Ctrl+C`) when done.

- [ ] **Step 4: Commit**

```bash
git add dashboard/components/SubscribeButton.tsx
git commit -m "feat: redesign notification UI as a bell + info icon pair"
```

---

### Task 4: Reposition the header cluster (bell+info above the switch)

**Files:**
- Modify: `dashboard/app/page.tsx`

- [ ] **Step 1: Stack the two components vertically instead of side by side**

In `dashboard/app/page.tsx`, find:

```tsx
        <div className="flex flex-wrap items-center gap-3">
          <ThemeToggle />
          <SubscribeButton />
        </div>
```

Replace with:

```tsx
        <div className="flex flex-col items-end gap-2">
          <SubscribeButton />
          <ThemeToggle />
        </div>
```

- [ ] **Step 2: Verify the type checker is clean**

Run: `cd dashboard && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Full manual verification in the dev server**

Run: `cd dashboard && npm run dev`, open `http://localhost:3000`.

1. Confirm the bell+info row renders directly above the theme switch, both right-aligned, matching the approved mockup.
2. Emulate a 375px mobile viewport and confirm the header's existing mobile-stacking behavior (logo/description first, then this control cluster as its own full-width row below it) still works — this cluster shouldn't overflow or look cramped at mobile width.
3. Widen back to desktop and confirm the side-by-side header layout (logo/description on the left, this cluster on the right) is unchanged from before this task.

- [ ] **Step 4: Run the production build**

Run: `cd dashboard && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/page.tsx
git commit -m "feat: stack bell/info above the theme switch in the header"
```

---

## Post-plan verification

Once pushed to `origin/main`, confirm live in production (footymodel.vercel.app): the switch toggles and persists correctly, a visitor with a stale `"system"` value (simulate via devtools) migrates cleanly to a real light/dark value, the bell glows only when subscribed, and the info popover opens/closes correctly on both mobile and desktop widths.
