"use client";

import { useEffect, useRef, useState } from "react";
import {
  persistNotificationPreference,
  readNotificationPreference,
} from "@/lib/notifications";
import { FaBell, FaBellSlash } from "react-icons/fa";
import { InfoIcon } from "@/components/icons";

type Status = "checking" | "unsupported" | "denied" | "off" | "on" | "working";

const INFO_TEXT: Record<Status, string> = {
  checking:
    "Checking whether push notifications are available in this browser. This usually takes a moment.",
  unsupported:
    "Push notifications aren't supported in this browser. On iPhone, add this page to your Home Screen first, then reopen it from there.",
  denied:
    "Notifications blocked. Enable them for this site in your browser settings to get alerts.",
  off: "Get notified when new picks are logged. Tap the bell to enable.",
  on: "Notifications on — you'll get alerts when new picks are logged. Tap the bell to turn off.",
  working: "Updating your notification preference…",
};

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

function vapidPublicKey(): string | null {
  const key = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
  return key && key.length > 0 ? key : null;
}

async function postSubscription(sub: PushSubscriptionJSON): Promise<boolean> {
  const res = await fetch("/api/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sub),
  });
  return res.ok;
}

async function deleteSubscription(sub: PushSubscriptionJSON): Promise<boolean> {
  const res = await fetch("/api/subscribe", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sub),
  });
  return res.ok;
}

export default function SubscribeButton() {
  const [status, setStatus] = useState<Status>("checking");
  const [infoOpen, setInfoOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const lastStableStatus = useRef<Exclude<Status, "checking" | "working">>("off");

  useEffect(() => {
    let cancelled = false;

    async function init() {
      const publicKey = vapidPublicKey();
      if (
        !publicKey ||
        !("serviceWorker" in navigator) ||
        !("PushManager" in window) ||
        !("Notification" in window)
      ) {
        if (!cancelled) {
          lastStableStatus.current = "unsupported";
          setStatus("unsupported");
        }
        return;
      }

      if (Notification.permission === "denied") {
        persistNotificationPreference("off");
        if (!cancelled) {
          lastStableStatus.current = "denied";
          setStatus("denied");
        }
        return;
      }

      try {
        await navigator.serviceWorker.register("/sw.js");
        const reg = await navigator.serviceWorker.ready;
        const existing = await reg.pushManager.getSubscription();
        const pref = readNotificationPreference();

        if (pref === "off" && existing) {
          await deleteSubscription(existing.toJSON());
          await existing.unsubscribe().catch(() => {});
          if (!cancelled) {
            lastStableStatus.current = "off";
            setStatus("off");
          }
          return;
        }

        if (existing) {
          const synced = await postSubscription(existing.toJSON());
          if (!cancelled) {
            if (synced) {
              persistNotificationPreference("on");
              lastStableStatus.current = "on";
              setStatus("on");
            } else {
              persistNotificationPreference("off");
              lastStableStatus.current = "off";
              setStatus("off");
            }
          }
          return;
        }

        if (pref === "on" && Notification.permission === "granted") {
          const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicKey),
          });
          const synced = await postSubscription(sub.toJSON());
          if (!cancelled) {
            if (synced) {
              persistNotificationPreference("on");
              lastStableStatus.current = "on";
              setStatus("on");
            } else {
              await sub.unsubscribe().catch(() => {});
              persistNotificationPreference("off");
              lastStableStatus.current = "off";
              setStatus("off");
            }
          }
          return;
        }

        if (pref === "off") {
          if (!cancelled) {
            lastStableStatus.current = "off";
            setStatus("off");
          }
          return;
        }

        if (!cancelled) {
          lastStableStatus.current = "off";
          setStatus("off");
        }
      } catch {
        if (!cancelled) {
          lastStableStatus.current = "unsupported";
          setStatus("unsupported");
        }
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!infoOpen) return;
    function onDocClick(e: MouseEvent) {
      if (!wrapperRef.current?.contains(e.target as Node)) setInfoOpen(false);
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, [infoOpen]);

  async function subscribe() {
    const publicKey = vapidPublicKey();
    if (!publicKey) {
      lastStableStatus.current = "unsupported";
      setStatus("unsupported");
      return;
    }
    setStatus("working");
    try {
      const reg = await navigator.serviceWorker.ready;
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        persistNotificationPreference("off");
        const next = permission === "denied" ? "denied" : "off";
        lastStableStatus.current = next;
        setStatus(next);
        return;
      }
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });
      const synced = await postSubscription(sub.toJSON());
      if (!synced) {
        await sub.unsubscribe().catch(() => {});
        persistNotificationPreference("off");
        lastStableStatus.current = "off";
        setStatus("off");
        return;
      }
      persistNotificationPreference("on");
      lastStableStatus.current = "on";
      setStatus("on");
    } catch {
      persistNotificationPreference("off");
      lastStableStatus.current = "off";
      setStatus("off");
    }
  }

  async function unsubscribe() {
    setStatus("working");
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        const removed = await deleteSubscription(sub.toJSON());
        await sub.unsubscribe().catch(() => {});
        if (!removed) {
          lastStableStatus.current = "on";
          setStatus("on");
          return;
        }
      }
      persistNotificationPreference("off");
      lastStableStatus.current = "off";
      setStatus("off");
    } catch {
      lastStableStatus.current = "off";
      setStatus("off");
      persistNotificationPreference("off");
    }
  }

  const interactive = status === "off" || status === "on";
  const bellActive = status === "on";
  const infoText =
    status === "working" ? INFO_TEXT[lastStableStatus.current] : INFO_TEXT[status];

  function handleBellClick() {
    if (status === "on") void unsubscribe();
    else if (status === "off") void subscribe();
  }

  return (
    <div ref={wrapperRef} className="relative flex items-center gap-2">
      <button
        type="button"
        onClick={handleBellClick}
        disabled={!interactive}
        aria-label={
          status === "on"
            ? "Notifications on - tap to turn off"
            : status === "off"
              ? "Get notified of new picks"
              : status === "denied"
                ? "Notifications blocked"
                : status === "checking"
                  ? "Checking notification support"
                  : "Notifications unsupported in this browser"
        }
        className={`w-9 h-9 rounded-full border flex items-center justify-center transition-opacity duration-300 ${
          bellActive
            ? "border-indigo-800 dark:border-indigo-400 text-indigo-600 dark:text-indigo-300 animate-bell-glow"
            : "border-neutral-200 dark:border-neutral-800 text-neutral-500 dark:text-neutral-400"
        } ${status === "working" || status === "checking" ? "opacity-50" : ""} ${
          interactive ? "hover:border-neutral-300 dark:hover:border-neutral-700" : "cursor-default"
        }`}
      >
        {bellActive ? (
          <FaBell className="w-[18px] h-[18px]" aria-hidden="true" />
        ) : (
          <FaBellSlash className="w-[18px] h-[18px]" aria-hidden="true" />
        )}
      </button>
      <button
        type="button"
        onClick={() => setInfoOpen((o) => !o)}
        aria-expanded={infoOpen}
        aria-label="About notifications"
        className="w-9 h-9 rounded-full border border-neutral-200 dark:border-neutral-800 flex items-center justify-center text-neutral-500 dark:text-neutral-400 hover:border-neutral-300 dark:hover:border-neutral-700"
      >
        <InfoIcon />
      </button>
      {infoOpen && (
        <div
          role="tooltip"
          className="absolute top-full right-0 mt-2 w-64 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3 text-xs leading-relaxed text-neutral-600 dark:text-neutral-400 shadow-lg z-20"
        >
          {infoText}
        </div>
      )}
    </div>
  );
}
