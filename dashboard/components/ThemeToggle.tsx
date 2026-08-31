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
