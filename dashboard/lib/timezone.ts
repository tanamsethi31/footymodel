/** All user-facing kickoff buckets and labels use Ireland (Europe/Dublin). */
export const APP_TIMEZONE = "Europe/Dublin";

export function kickoffMs(kickoff: string): number {
  const t = new Date(kickoff).getTime();
  return Number.isFinite(t) ? t : 0;
}

/** Calendar date of kickoff in Irish local time (YYYY-MM-DD). */
export function irishDateKey(kickoff: string): string {
  const t = new Date(kickoff);
  if (Number.isNaN(t.getTime())) return kickoff.slice(0, 10);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: APP_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(t);
  const y = parts.find((p) => p.type === "year")?.value;
  const m = parts.find((p) => p.type === "month")?.value;
  const d = parts.find((p) => p.type === "day")?.value;
  return y && m && d ? `${y}-${m}-${d}` : t.toISOString().slice(0, 10);
}

export function todayIrishDateKey(nowMs = Date.now()): string {
  return irishDateKey(new Date(nowMs).toISOString());
}
