import { NextRequest, NextResponse } from "next/server";
import type { PushSubscription } from "web-push";
import { getAllSubscriptions, removeSubscription } from "@/lib/redis";
import { sendPush } from "@/lib/push";

// Called by live_poll.yml right after it commits new prediction rows -
// not polled, so notifications go out the moment a real fixture is logged.
export async function POST(req: NextRequest) {
  const secret = req.headers.get("x-notify-secret");
  if (!secret || secret !== process.env.NOTIFY_SECRET) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { title, body, url } = await req.json();
  if (!title || !body) {
    return NextResponse.json({ error: "title and body required" }, { status: 400 });
  }

  const subs = (await getAllSubscriptions()) as PushSubscription[];
  let sent = 0;
  let pruned = 0;
  await Promise.all(
    subs.map(async (sub) => {
      const result = await sendPush(sub, { title, body, url });
      if (result.ok) {
        sent++;
      } else if (result.expired) {
        await removeSubscription(sub);
        pruned++;
      }
    })
  );

  return NextResponse.json({ sent, pruned, total: subs.length });
}
