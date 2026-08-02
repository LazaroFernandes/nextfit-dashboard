import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTvToken } from "@/lib/settings";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  const id = request.nextUrl.searchParams.get("id");
  const device = request.nextUrl.searchParams.get("device") || "tv-principal";
  if (!(await validateTvToken(token))) return NextResponse.json({ error: "Token inválido" }, { status: 401 });
  if (id) await db.welcomeQueue.updateMany({ where: { id, status: { in: ["PENDING", "DISPLAYING"] } }, data: { status: "COMPLETED", displayedAt: new Date(), completedAt: new Date() } });
  const destination = new URL("/tv", request.url);
  destination.searchParams.set("token", token || "");
  destination.searchParams.set("device", device);
  return NextResponse.redirect(destination);
}
