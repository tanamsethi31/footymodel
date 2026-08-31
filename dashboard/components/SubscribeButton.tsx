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
        <div className="absolute top-full right-0 mt-10 w-64 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3 text-xs text-neutral-500 dark:text-neutral-400 shadow-lg z-20">
          {DESCRIPTIONS[status]}
        </div>
      )}
    </div>
  );
}
