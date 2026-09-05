"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FaBell, FaBellSlash } from "react-icons/fa";
import {
  persistNotificationPreference,
  readNotificationPreference,
} from "@/lib/notifications";
import { InfoIcon } from "@/components/icons";
import { resolveVapidPublicKey, urlBase64ToUint8Array } from "@/lib/vapid";

type Status = "checking" | "unsupported" | "denied" | "off" | "on" | "working";

const INFO_TEXT: Record<Status, string> = {
  checking:
    "Checking whether push notifications are available in this browser. This usually takes a moment.",
  unsupported:
    "Push notifications aren't supported in this browser, or the server push key isn't configured yet. On iPhone, add this page to your Home Screen first, then reopen it from there.",
  denied:
    "Notifications blocked. Enable them for this site in your browser settings, then tap the bell again.",
  off: "Get notified when new picks are logged. Tap the bell to enable.",
  on: "Notifications on — you'll get alerts when new picks are logged. Tap the bell to turn off.",
  working: "Updating your notification preference…",
};

async function fetchPublicKey(): Promise<string | null> {
  const buildTimeKey = resolveVapidPublicKey(process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY);
  if (buildTimeKey) return buildTimeKey;
  try {
    const res = await fetch("/api/push-config");
    if (!res.ok) return null;
    const body = (await res.json()) as { publicKey?: string };
    return resolveVapidPublicKey(body.publicKey);
  } catch {
    return null;
  }
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

function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export default function SubscribeButton() {
  const [status, setStatus] = useState<Status>("checking");
  const [infoOpen, setInfoOpen] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const publicKeyRef = useRef<string | null>(null);
  const initDoneRef = useRef(false);
  const lastStableStatus = useRef<Exclude<Status, "checking" | "working">>("off");

  const syncFromBrowser = useCallback(async (publicKey: string | null): Promise<Exclude<Status, "working">> => {
    if (!pushSupported()) {
      lastStableStatus.current = "unsupported";
      setStatus("unsupported");
      return "unsupported";
    }

    if (Notification.permission === "denied") {
      persistNotificationPreference("off");
      lastStableStatus.current = "denied";
      setStatus("denied");
      return "denied";
    }

    if (!publicKey) {
      lastStableStatus.current = "unsupported";
      setStatus("unsupported");
      return "unsupported";
    }

    try {
      await navigator.serviceWorker.register("/sw.js");
      const reg = await navigator.serviceWorker.ready;
      const existing = await reg.pushManager.getSubscription();
      const pref = readNotificationPreference();

      if (pref === "off" && existing) {
        await deleteSubscription(existing.toJSON());
        await existing.unsubscribe().catch(() => {});
        lastStableStatus.current = "off";
        setStatus("off");
        return "off";
      }

      if (existing) {
        const synced = await postSubscription(existing.toJSON());
        if (synced) {
          persistNotificationPreference("on");
          lastStableStatus.current = "on";
          setStatus("on");
          return "on";
        }
        persistNotificationPreference("off");
        lastStableStatus.current = "off";
        setStatus("off");
        setErrorText("Could not save your subscription on the server. Tap the bell to try again.");
        return "off";
      }

      if (pref === "on" && Notification.permission === "granted") {
        const sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource,
        });
        const synced = await postSubscription(sub.toJSON());
        if (synced) {
          persistNotificationPreference("on");
          lastStableStatus.current = "on";
          setStatus("on");
          return "on";
        }
        await sub.unsubscribe().catch(() => {});
        persistNotificationPreference("off");
        lastStableStatus.current = "off";
        setStatus("off");
        setErrorText("Could not save your subscription on the server. Tap the bell to try again.");
        return "off";
      }

      lastStableStatus.current = "off";
      setStatus("off");
      return "off";
    } catch {
      lastStableStatus.current = "unsupported";
      setStatus("unsupported");
      setErrorText("Could not set up notifications in this browser. Try a hard refresh.");
      return "unsupported";
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      const publicKey = await fetchPublicKey();
      if (cancelled) return;
      publicKeyRef.current = publicKey;
      await syncFromBrowser(publicKey);
      if (!cancelled) initDoneRef.current = true;
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, [syncFromBrowser]);

  useEffect(() => {
    if (!infoOpen) return;
    function onDocClick(e: MouseEvent) {
      if (!wrapperRef.current?.contains(e.target as Node)) setInfoOpen(false);
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, [infoOpen]);

  async function subscribe() {
    setErrorText(null);
    const publicKey = publicKeyRef.current ?? (await fetchPublicKey());
    publicKeyRef.current = publicKey;

    if (!pushSupported() || !publicKey) {
      lastStableStatus.current = "unsupported";
      setStatus("unsupported");
      setInfoOpen(true);
      setErrorText("Notifications are not available right now. The push key may not be configured on the server.");
      return;
    }

    if (Notification.permission === "denied") {
      lastStableStatus.current = "denied";
      setStatus("denied");
      setInfoOpen(true);
      return;
    }

    setStatus("working");
    try {
      await navigator.serviceWorker.register("/sw.js");
      const reg = await navigator.serviceWorker.ready;

      if (Notification.permission !== "granted") {
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
          persistNotificationPreference("off");
          const next = permission === "denied" ? "denied" : "off";
          lastStableStatus.current = next;
          setStatus(next);
          if (next === "denied") setInfoOpen(true);
          return;
        }
      }

      let sub = await reg.pushManager.getSubscription();
      if (!sub) {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource,
        });
      }

      const synced = await postSubscription(sub.toJSON());
      if (!synced) {
        await sub.unsubscribe().catch(() => {});
        persistNotificationPreference("off");
        lastStableStatus.current = "off";
        setStatus("off");
        setInfoOpen(true);
        setErrorText("Could not save your subscription. The notification store may be unavailable — try again in a moment.");
        return;
      }

      persistNotificationPreference("on");
      lastStableStatus.current = "on";
      setStatus("on");
    } catch (err) {
      persistNotificationPreference("off");
      lastStableStatus.current = "off";
      setStatus("off");
      setInfoOpen(true);
      setErrorText(
        err instanceof Error
          ? `Could not enable notifications: ${err.message}`
          : "Could not enable notifications. Check browser permission settings and try again."
      );
    }
  }

  async function unsubscribe() {
    setErrorText(null);
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
          setInfoOpen(true);
          setErrorText("Could not remove your subscription from the server. Try again.");
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

  const bellActive = status === "on";
  const infoText =
    errorText ??
    (status === "working" ? INFO_TEXT[lastStableStatus.current] : INFO_TEXT[status]);

  async function handleBellClick() {
    if (status === "working") return;

    let resolved: Exclude<Status, "working">;
    if (!initDoneRef.current) {
      const publicKey = publicKeyRef.current ?? (await fetchPublicKey());
      publicKeyRef.current = publicKey;
      resolved = await syncFromBrowser(publicKey);
      initDoneRef.current = true;
    } else {
      resolved = status as Exclude<Status, "working">;
    }

    if (resolved === "on") {
      await unsubscribe();
      return;
    }

    if (resolved === "off" || resolved === "checking") {
      await subscribe();
      return;
    }

    setInfoOpen(true);
  }

  return (
    <div ref={wrapperRef} className="relative flex items-center gap-2">
      <button
        type="button"
        onClick={() => void handleBellClick()}
        disabled={status === "working"}
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
        } ${status === "working" || status === "checking" ? "opacity-70" : ""} ${
          status === "working" ? "cursor-wait" : "hover:border-neutral-300 dark:hover:border-neutral-700"
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
