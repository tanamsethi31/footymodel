export function formatKickoff(iso: string) {
  try {
    // Explicit timeZone, not the runtime's local one - some panels render
    // server-side (Vercel's server clock) and some render client-side (the
    // viewer's own browser clock), which would otherwise show two different
    // times for the same kickoff depending on which tab you're looking at.
    const formatted = new Date(iso).toLocaleString("en-GB", {
      timeZone: "Asia/Kolkata",
      weekday: "short",
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
    return `${formatted} IST`;
  } catch {
    return iso;
  }
}

export function pct(n: number | null) {
  return n === null ? "-" : `${(n * 100).toFixed(1)}%`;
}

export function odds(n: number | null) {
  return n === null ? "-" : n.toFixed(2);
}

export function EvBadge({ ev }: { ev: number | null }) {
  if (ev === null) return <span className="text-neutral-400">-</span>;
  const positive = ev > 0;
  return (
    <span
      className={`font-mono font-medium ${
        positive
          ? "text-emerald-600 dark:text-emerald-400"
          : "text-red-500 dark:text-red-400"
      }`}
    >
      {positive ? "+" : ""}
      {(ev * 100).toFixed(1)}%
    </span>
  );
}

export const SOURCE_LABEL: Record<string, string> = {
  "api-football": "API-Football",
  sofascore: "SofaScore",
  rapidapi: "RapidAPI",
};

export function probClass(p: number | null) {
  if (p === null) return "text-neutral-300 dark:text-neutral-700";
  if (p >= 0.5) return "text-emerald-600 dark:text-emerald-400";
  if (p >= 0.2) return "text-neutral-700 dark:text-neutral-300";
  return "text-neutral-400 dark:text-neutral-600";
}
