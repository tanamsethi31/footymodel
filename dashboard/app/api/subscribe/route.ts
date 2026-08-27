import { NextRequest, NextResponse } from "next/server";
import { addSubscription, removeSubscription } from "@/lib/redis";

export async function POST(req: NextRequest) {
  const body = await req.json();
  if (!body?.endpoint) {
    return NextResponse.json({ error: "invalid subscription" }, { status: 400 });
  }
  await addSubscription(body);
  return NextResponse.json({ ok: true });
}

export async function DELETE(req: NextRequest) {
  const body = await req.json();
  if (!body?.endpoint) {
    return NextResponse.json({ error: "invalid subscription" }, { status: 400 });
  }
  await removeSubscription(body);
  return NextResponse.json({ ok: true });
}
