import { NextRequest, NextResponse } from "next/server";
import { adminOrUnauthorized } from "@/lib/auth-api";
import { db } from "@/lib/db";
import { emitTvEvent } from "@/lib/events";
import { birthdaySchema } from "@/lib/schemas";

export async function POST(request: NextRequest) {
  const auth = await adminOrUnauthorized(); if ("response" in auth) return auth.response; const raw = await request.json(); const rows = Array.isArray(raw) ? raw : [raw];
  if (rows.length > 500) return NextResponse.json({ error: "Máximo de 500 registros por importação" }, { status: 400 });
  const parsed = rows.map((row) => birthdaySchema.safeParse(row)); if (parsed.some((item) => !item.success)) return NextResponse.json({ error: "Dados inválidos", details: parsed.filter((item) => !item.success) }, { status: 400 });
  const created = await db.$transaction(parsed.map((item) => { const value = item.data!; return db.birthday.create({ data: { name: value.name.replace(/[<>]/g, ""), birthDate: noonUtc(value.birthDate), photoUrl: value.photoUrl || null, message: value.message || null, showLastName: value.showLastName, active: value.active, externalSource: "MANUAL" } }); }));
  await db.auditLog.create({ data: { adminUserId: auth.session.sub, action: rows.length > 1 ? "IMPORT" : "CREATE", entity: "Birthday", details: { count: created.length } } }); emitTvEvent({ type: "playlist.reload" }); return NextResponse.json(created, { status: 201 });
}
function noonUtc(value: string) { const date = value.slice(0,10); return new Date(`${date}T12:00:00.000Z`); }
