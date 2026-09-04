export const NOTIFICATIONS_PREF_KEY = "notifications-enabled";

export type NotificationPreference = "on" | "off";

export function readNotificationPreference(): NotificationPreference | null {
  try {
    const stored = localStorage.getItem(NOTIFICATIONS_PREF_KEY);
    if (stored === "on" || stored === "off") return stored;
  } catch {
    // localStorage unavailable.
  }
  return null;
}

export function persistNotificationPreference(pref: NotificationPreference) {
  try {
    localStorage.setItem(NOTIFICATIONS_PREF_KEY, pref);
  } catch {
    // Preference still applies for this session via in-memory state.
  }
}
