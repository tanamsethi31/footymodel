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

export async function addSubscription(sub: unknown): Promise<void> {
  await getRedis().sadd(SUBS_KEY, JSON.stringify(sub));
}

export async function removeSubscription(sub: unknown): Promise<void> {
  await getRedis().srem(SUBS_KEY, JSON.stringify(sub));
}

export async function getAllSubscriptions(): Promise<unknown[]> {
  const raw = await getRedis().smembers(SUBS_KEY);
  return raw.map((s) => (typeof s === "string" ? JSON.parse(s) : s));
}
