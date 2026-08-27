import webpush, { type PushSubscription } from "web-push";

let configured = false;

function ensureConfigured() {
  if (configured) return;
  const publicKey = process.env.VAPID_PUBLIC_KEY;
  const privateKey = process.env.VAPID_PRIVATE_KEY;
  if (!publicKey || !privateKey) {
    throw new Error("VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY not set");
  }
  webpush.setVapidDetails(
    "mailto:sethit@tcd.ie",
    publicKey,
    privateKey
  );
  configured = true;
}

export async function sendPush(
  subscription: PushSubscription,
  payload: { title: string; body: string; url?: string }
): Promise<{ ok: boolean; expired: boolean }> {
  ensureConfigured();
  try {
    await webpush.sendNotification(subscription, JSON.stringify(payload));
    return { ok: true, expired: false };
  } catch (err) {
    const statusCode = (err as { statusCode?: number }).statusCode;
    // 404/410 means the subscription is gone (user revoked, browser data
    // cleared) - the caller should drop it rather than keep retrying forever.
    const expired = statusCode === 404 || statusCode === 410;
    return { ok: false, expired };
  }
}
