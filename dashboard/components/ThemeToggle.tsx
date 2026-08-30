"use client";

import { useEffect, useState } from "react";

type ThemePreference = "light" | "dark" | "system";

const OPTIONS: { value: ThemePreference; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

function systemPrefersDark(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
}

function applyTheme(preference: ThemePreference) {
  const isDark = preference === "dark" || (preference === "system" && systemPrefersDark());
  document.documentElement.classList.toggle("dark", isDark);
}

function readStoredPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem("theme");
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

export default function ThemeToggle() {
  const [preference, setPreference] = useState<ThemePreference>("system");

  // Correct the default "system" guess to whatever's actually stored, right
  // after mount - avoids a server/client render mismatch on the initial paint.
  // Also re-applies the resolved class here, not just reads state: React
  // Strict Mode's dev-only remount resets <html> to only the attributes in
  // its JSX, stripping whatever class layout.tsx's pre-hydration script added
  // imperatively - without this, a stored "dark"/"light" preference would
  // flash correctly then flip back on every dev hard-reload (production has
  // no such remount, so this only matters in `npm run dev`).
  useEffect(() => {
    const stored = readStoredPreference();
    setPreference(stored);
    applyTheme(stored);
  }, []);

  // While following the OS preference, keep the page in sync live if the OS
  // theme changes while this tab is open.
  useEffect(() => {
    if (preference !== "system") return;
    if (typeof window.matchMedia !== "function") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [preference]);

  function choose(value: ThemePreference) {
    setPreference(value);
    applyTheme(value);
    try {
      if (value === "system") {
        localStorage.removeItem("theme");
      } else {
        localStorage.setItem("theme", value);
      }
    } catch {
      // localStorage unavailable (e.g. private browsing) - the theme still
      // applies for this session via the direct class toggle above, it just
      // won't persist across a reload.
    }
  }

  return (
    <div className="inline-flex bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-lg p-0.5 gap-0.5">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => choose(opt.value)}
          className={`px-3 py-1 rounded-md text-xs font-medium transition-colors duration-150 active:scale-95 ${
            preference === opt.value
              ? "bg-white dark:bg-neutral-100 text-neutral-900"
              : "text-neutral-500 dark:text-neutral-400"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
