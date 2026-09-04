"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { persistLastRefreshAt } from "@/lib/refresh";

async function refreshDashboard(router: ReturnType<typeof useRouter>) {
  try {
    const res = await fetch("/api/revalidate", { method: "POST" });
    if (res.ok) {
      persistLastRefreshAt(Date.now());
      router.refresh();
    }
  } catch {
    router.refresh();
  }
}

export default function DashboardRefreshListener() {
  const router = useRouter();

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.data?.type === "DASHBOARD_REFRESH") {
        void refreshDashboard(router);
      }
    }
    navigator.serviceWorker?.addEventListener("message", onMessage);
    return () => navigator.serviceWorker?.removeEventListener("message", onMessage);
  }, [router]);

  return null;
}
