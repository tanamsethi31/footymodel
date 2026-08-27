"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "unsupported" | "denied" | "off" | "on" | "working";

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

export default function SubscribeButton() {
  const [status, setStatus] = useState<Status>("checking");

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
  if (status === "unsupported")
    return (
      <p className="text-sm text-neutral-500">
        Push notifications aren&apos;t supported in this browser. On iPhone,
        add this page to your Home Screen first, then reopen it from there.
      </p>
    );
  if (status === "denied")
    return (
      <p className="text-sm text-neutral-500">
        Notifications blocked — enable them for this site in your browser
        settings to get alerts.
      </p>
    );

  return (
    <button
      onClick={status === "on" ? unsubscribe : subscribe}
      disabled={status === "working"}
      className="rounded-full border border-neutral-300 dark:border-neutral-700 px-4 py-1.5 text-sm font-medium hover:bg-neutral-100 dark:hover:bg-neutral-800 transition disabled:opacity-50"
    >
      {status === "on" && "🔔 Notifications on"}
      {status === "off" && "🔕 Get notified of new picks"}
      {status === "working" && "…"}
    </button>
  );
}
