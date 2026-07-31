import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { validateTvToken } from "@/lib/settings";

export async function POST(request: NextRequest) {
  if (!(await validateTvToken(request.nextUrl.searchParams.get("token")))) return NextResponse.json({ error: "Token inválido" }, { status: 401 });
  const { id } = await request.json() as { id?: string };
  if (!id) return NextResponse.json({ error: "ID ausente" }, { status: 400 });
  await db.welcomeQueue.updateMany({ where: { id }, data: { status: "COMPLETED", completedAt: new Date() } });
  return NextResponse.json({ ok: true });
}
