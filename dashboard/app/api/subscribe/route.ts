import { NextRequest, NextResponse } from "next/server";
import { addSubscription, removeSubscription } from "@/lib/redis";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    if (!body?.endpoint) {
      return NextResponse.json({ error: "invalid_subscription" }, { status: 400 });
    }
    await addSubscription(body);
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: "storage_unavailable" }, { status: 503 });
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const body = await req.json();
    if (!body?.endpoint) {
      return NextResponse.json({ error: "invalid_subscription" }, { status: 400 });
    }
    await removeSubscription(body);
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: "storage_unavailable" }, { status: 503 });
  }
}
