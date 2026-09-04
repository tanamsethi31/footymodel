"use client";

import { useEffect, useState } from "react";
import { MdDarkMode, MdLightMode } from "react-icons/md";

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
    // localStorage unavailable.
  }
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

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
      type="button"
      onClick={toggle}
      role="switch"
      aria-checked={theme === "dark"}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      className="relative w-[52px] h-7 rounded-full border border-neutral-200 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-900 transition-colors duration-200"
    >
      <span
        className={`absolute left-0.5 top-0.5 flex items-center justify-center w-6 h-6 rounded-full bg-white dark:bg-neutral-800 shadow-sm text-neutral-500 dark:text-neutral-400 transition-transform duration-200 ${
          theme === "dark" ? "translate-x-6" : "translate-x-0"
        }`}
      >
        {theme === "dark" ? (
          <MdDarkMode className="w-4 h-4" aria-hidden="true" />
        ) : (
          <MdLightMode className="w-4 h-4" aria-hidden="true" />
        )}
      </span>
    </button>
  );
}
