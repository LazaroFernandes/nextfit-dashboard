import { NextRequest, NextResponse } from "next/server";
import { unlink } from "node:fs/promises";
import path from "node:path";
import { adminOrUnauthorized } from "@/lib/auth-api";
import { db } from "@/lib/db";
import { emitTvEvent } from "@/lib/events";

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const auth = await adminOrUnauthorized(); if ("response" in auth) return auth.response; const { id } = await params; const body = await request.json();
  const item = await db.sponsorMedia.update({ where: { id }, data: { name: body.name?.slice(0,100), durationSec: integer(body.durationSec, 3, 300), sortOrder: integer(body.sortOrder, 0, 9999), priority: integer(body.priority, 0, 100), active: typeof body.active === "boolean" ? body.active : undefined, sponsorName: body.sponsorName?.slice(0,100) || null } });
  await db.auditLog.create({ data: { adminUserId: auth.session.sub, action: "UPDATE", entity: "SponsorMedia", entityId: id } }); emitTvEvent({ type: "playlist.reload" }); return NextResponse.json(item);
}
export async function DELETE(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const auth = await adminOrUnauthorized(); if ("response" in auth) return auth.response; const { id } = await params; const item = await db.sponsorMedia.delete({ where: { id } });
  if (item.fileUrl.startsWith("/uploads/")) await unlink(path.join(process.cwd(), "public", item.fileUrl)).catch(() => undefined);
  await db.auditLog.create({ data: { adminUserId: auth.session.sub, action: "DELETE", entity: "SponsorMedia", entityId: id, details: { name: item.name } } }); emitTvEvent({ type: "playlist.reload" }); return NextResponse.json({ ok: true });
}
function integer(value: unknown, min: number, max: number) { if (value === undefined) return undefined; const number = Number(value); return Number.isFinite(number) ? Math.min(max, Math.max(min, Math.round(number))) : undefined; }
