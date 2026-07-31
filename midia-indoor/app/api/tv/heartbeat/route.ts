import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { getSettings, validateTvToken } from "@/lib/settings";

export async function POST(request: NextRequest) {
  if (!(await validateTvToken(request.nextUrl.searchParams.get("token")))) return NextResponse.json({ error: "Token inválido" }, { status: 401 });
  const body = await request.json() as { device?: string; currentMedia?: string | null };
  const settings = await getSettings();
  await db.displayDevice.upsert({ where: { name: body.device || "tv-principal" }, create: { name: body.device || "tv-principal", unitId: settings.unitId, status: "ONLINE", lastSeenAt: new Date(), currentMedia: body.currentMedia }, update: { status: "ONLINE", lastSeenAt: new Date(), currentMedia: body.currentMedia } });
  return NextResponse.json({ ok: true });
}
