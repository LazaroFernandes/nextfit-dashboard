import { NextRequest } from "next/server";
import { db } from "@/lib/db";
import { tvEventBus, type TvEvent } from "@/lib/events";
import { getSettings, validateTvToken } from "@/lib/settings";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  if (!(await validateTvToken(token))) return new Response("Unauthorized", { status: 401 });
  const deviceName = request.nextUrl.searchParams.get("device") || "tv-principal";
  const settings = await getSettings();
  const device = await db.displayDevice.upsert({ where: { name: deviceName }, create: { name: deviceName, unitId: settings.unitId, status: "ONLINE", lastSeenAt: new Date() }, update: { status: "ONLINE", lastSeenAt: new Date() } });
  const connection = await db.displayConnection.create({ data: { deviceId: device.id, ipAddress: request.headers.get("x-forwarded-for"), userAgent: request.headers.get("user-agent") } });
  const encoder = new TextEncoder();
  let keepAlive: ReturnType<typeof setInterval>;
  let closed = false;
  const stream = new ReadableStream({
    start(controller) {
      const send = (event: TvEvent) => { if (!closed) controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`)); };
      send({ type: "playlist.reload", payload: { connected: true } });
      tvEventBus.on("tv", send);
      keepAlive = setInterval(() => { if (!closed) controller.enqueue(encoder.encode(": keepalive\n\n")); }, 20_000);
      request.signal.addEventListener("abort", () => {
        closed = true; clearInterval(keepAlive); tvEventBus.off("tv", send);
        void db.displayConnection.update({ where: { id: connection.id }, data: { disconnectedAt: new Date() } }).catch(() => undefined);
      });
    },
    cancel() { closed = true; clearInterval(keepAlive); },
  });
  return new Response(stream, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", Connection: "keep-alive", "X-Accel-Buffering": "no" } });
}
