import { NextResponse } from "next/server";
import { resolveVapidPublicKey } from "@/lib/vapid";

export async function GET() {
  const publicKey = resolveVapidPublicKey(
    process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
    process.env.VAPID_PUBLIC_KEY
  );
  if (!publicKey) {
    return NextResponse.json({ error: "not_configured" }, { status: 503 });
  }
  return NextResponse.json({ publicKey });
}
