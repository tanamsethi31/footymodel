export const REFRESH_COOLDOWN_MS = 60_000;
export const LAST_REFRESH_KEY = "dashboard-last-refresh";

export function readLastRefreshAt(): number | null {
  try {
    const raw = localStorage.getItem(LAST_REFRESH_KEY);
    if (!raw) return null;
    const ts = Number(raw);
    return Number.isFinite(ts) ? ts : null;
  } catch {
    return null;
  }
}

export function persistLastRefreshAt(ts: number) {
  try {
    localStorage.setItem(LAST_REFRESH_KEY, String(ts));
  } catch {
    // Cooldown still enforced for this session via component state.
  }
}

export function msUntilRefreshAllowed(now = Date.now()): number {
  const last = readLastRefreshAt();
  if (last === null) return 0;
  return Math.max(0, REFRESH_COOLDOWN_MS - (now - last));
}
