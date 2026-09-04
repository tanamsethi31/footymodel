import { NextRequest, NextResponse } from "next/server";
import { revalidatePath } from "next/cache";
import { getRedis } from "@/lib/redis";
import { REFRESH_COOLDOWN_MS } from "@/lib/refresh";

const RATE_LIMIT_PREFIX = "refresh:limit:";

function clientKey(req: NextRequest): string {
  const forwarded = req.headers.get("x-forwarded-for");
  const ip = forwarded?.split(",")[0]?.trim() || req.headers.get("x-real-ip") || "anonymous";
  return `${RATE_LIMIT_PREFIX}${ip}`;
}

export async function POST(req: NextRequest) {
  const key = clientKey(req);
  try {
    const redis = getRedis();
    const blocked = await redis.get<string>(key);
    if (blocked) {
      const retryAfter = await redis.ttl(key);
      return NextResponse.json(
        { error: "rate_limited", retryAfter: Math.max(retryAfter, 1) },
        { status: 429 }
      );
    }
    await redis.set(key, "1", { ex: Math.ceil(REFRESH_COOLDOWN_MS / 1000) });
  } catch {
    // Redis unavailable during build/preview — still allow a refresh.
  }

  revalidatePath("/");
  return NextResponse.json({
    ok: true,
    revalidatedAt: new Date().toISOString(),
    cooldownMs: REFRESH_COOLDOWN_MS,
  });
}
