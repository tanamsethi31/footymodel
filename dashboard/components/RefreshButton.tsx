"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  msUntilRefreshAllowed,
  persistLastRefreshAt,
  REFRESH_COOLDOWN_MS,
} from "@/lib/refresh";
import { RefreshIcon } from "@/components/icons";

type RefreshState = "idle" | "refreshing" | "cooldown";

function formatCountdown(ms: number): string {
  const secs = Math.ceil(ms / 1000);
  return secs <= 1 ? "1s" : `${secs}s`;
}

export default function RefreshButton() {
  const router = useRouter();
  const [state, setState] = useState<RefreshState>("idle");
  const [countdownMs, setCountdownMs] = useState(0);

  useEffect(() => {
    const remaining = msUntilRefreshAllowed();
    if (remaining > 0) {
      setCountdownMs(remaining);
      setState("cooldown");
    }
  }, []);

  useEffect(() => {
    if (state !== "cooldown" || countdownMs <= 0) return;
    const timer = window.setInterval(() => {
      const remaining = msUntilRefreshAllowed();
      if (remaining <= 0) {
        setCountdownMs(0);
        setState("idle");
        return;
      }
      setCountdownMs(remaining);
    }, 250);
    return () => window.clearInterval(timer);
  }, [state, countdownMs]);

  async function refresh() {
    const blockedFor = msUntilRefreshAllowed();
    if (state === "refreshing" || blockedFor > 0) {
      setCountdownMs(blockedFor);
      setState("cooldown");
      return;
    }

    setState("refreshing");
    try {
      const res = await fetch("/api/revalidate", { method: "POST" });
      if (res.status === 429) {
        const body = (await res.json()) as { retryAfter?: number };
        const retryMs = (body.retryAfter ?? REFRESH_COOLDOWN_MS / 1000) * 1000;
        persistLastRefreshAt(Date.now() - REFRESH_COOLDOWN_MS + retryMs);
        setCountdownMs(retryMs);
        setState("cooldown");
        return;
      }
      if (!res.ok) throw new Error(`refresh failed: ${res.status}`);
      persistLastRefreshAt(Date.now());
      router.refresh();
      setState("cooldown");
      setCountdownMs(REFRESH_COOLDOWN_MS);
    } catch {
      setState("idle");
    }
  }

  const disabled = state === "refreshing" || state === "cooldown";
  const label =
    state === "refreshing"
      ? "Refreshing data"
      : state === "cooldown"
        ? `Refresh available in ${formatCountdown(countdownMs)}`
        : "Refresh dashboard data";

  return (
    <button
      type="button"
      onClick={() => void refresh()}
      disabled={disabled}
      aria-label={label}
      title={label}
      className={`w-9 h-9 rounded-full border border-neutral-200 dark:border-neutral-800 flex items-center justify-center text-neutral-500 dark:text-neutral-400 transition-opacity duration-300 ${
        disabled ? "opacity-50 cursor-not-allowed" : "hover:border-neutral-300 dark:hover:border-neutral-700"
      } ${state === "refreshing" ? "animate-spin-slow" : ""}`}
    >
      <RefreshIcon />
    </button>
  );
}
