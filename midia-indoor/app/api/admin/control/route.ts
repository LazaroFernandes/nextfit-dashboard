import { NextRequest, NextResponse } from "next/server";
import { adminOrUnauthorized } from "@/lib/auth-api";
import { db } from "@/lib/db";
import { emitTvEvent, type TvEvent } from "@/lib/events";

const events: Record<string, TvEvent["type"]> = { reload: "screen.reload", playlist: "playlist.reload", clearQueue: "queue.clear", pause: "media.pause", resume: "media.resume" };
export async function POST(request: NextRequest) { const auth = await adminOrUnauthorized(); if ("response" in auth) return auth.response; const { action } = await request.json() as { action?: string }; const type = action && events[action]; if (!type) return NextResponse.json({ error: "Ação inválida" }, { status: 400 }); if (action === "clearQueue") await db.welcomeQueue.updateMany({ where: { status: { in: ["PENDING", "DISPLAYING"] } }, data: { status: "EXPIRED" } }); if (action === "pause" || action === "resume") await db.displayDevice.updateMany({ data: { paused: action === "pause" } }); emitTvEvent({ type }); await db.auditLog.create({ data: { adminUserId: auth.session.sub, action: `TV_${action.toUpperCase()}`, entity: "DisplayDevice" } }); return NextResponse.json({ ok: true }); }
