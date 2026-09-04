import { Redis } from "@upstash/redis";

// Lazy init - avoids crashing `next build` before Upstash env vars exist
// (e.g. first deploy, before the Marketplace integration is provisioned).
// Vercel's Upstash Marketplace integration names these KV_REST_API_* (not
// the UPSTASH_REDIS_REST_* names Redis.fromEnv() looks for by default) -
// verified against the actual provisioned env vars, so pass explicitly.
let _redis: Redis | null = null;

export function getRedis(): Redis {
  if (!_redis) {
    const url = process.env.KV_REST_API_URL;
    const token = process.env.KV_REST_API_TOKEN;
    if (!url || !token) throw new Error("KV_REST_API_URL / KV_REST_API_TOKEN not set");
    _redis = new Redis({ url, token });
  }
  return _redis;
}

const SUBS_KEY = "push:subscriptions";

type StoredSubscription = { endpoint?: string };

function serializeSubscription(sub: unknown): string {
  return JSON.stringify(sub);
}

async function allSubscriptionEntries(): Promise<Array<{ raw: string; sub: StoredSubscription }>> {
  const raw = await getRedis().smembers(SUBS_KEY);
  return raw.map((entry) => {
    const text = typeof entry === "string" ? entry : JSON.stringify(entry);
    try {
      return { raw: text, sub: JSON.parse(text) as StoredSubscription };
    } catch {
      return { raw: text, sub: {} };
    }
  });
}

export async function addSubscription(sub: unknown): Promise<void> {
  // Drop any prior row for the same browser endpoint before re-adding.
  await removeSubscription(sub);
  await getRedis().sadd(SUBS_KEY, serializeSubscription(sub));
}

export async function removeSubscription(sub: unknown): Promise<void> {
  const endpoint = (sub as StoredSubscription)?.endpoint;
  if (!endpoint) return;
  const entries = await allSubscriptionEntries();
  for (const entry of entries) {
    if (entry.sub.endpoint === endpoint) {
      await getRedis().srem(SUBS_KEY, entry.raw);
      return;
    }
  }
}

export async function getAllSubscriptions(): Promise<unknown[]> {
  const entries = await allSubscriptionEntries();
  return entries.map((entry) => entry.sub);
}

export async function hasSubscription(endpoint: string): Promise<boolean> {
  const entries = await allSubscriptionEntries();
  return entries.some((entry) => entry.sub.endpoint === endpoint);
}
