import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { db } from "@/lib/db";
import { createSession } from "@/lib/security";
import { allowRequest } from "@/lib/rate-limit";

const schema = z.object({ email: z.email(), password: z.string().min(8).max(200) });
export async function POST(request: NextRequest) {
  const ip = request.headers.get("x-forwarded-for") || "login";
  if (!allowRequest(`login:${ip}`, 10, 5 * 60_000)) return NextResponse.json({ error: "Muitas tentativas" }, { status: 429 });
  const parsed = schema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "Credenciais inválidas" }, { status: 400 });
  const user = await db.adminUser.findUnique({ where: { email: parsed.data.email.toLowerCase() } });
  if (!user?.active || !(await bcrypt.compare(parsed.data.password, user.passwordHash))) return NextResponse.json({ error: "Credenciais inválidas" }, { status: 401 });
  await createSession({ sub: user.id, email: user.email, name: user.name });
  await db.auditLog.create({ data: { adminUserId: user.id, action: "LOGIN", entity: "AdminUser", entityId: user.id, ipAddress: ip } });
  return NextResponse.json({ ok: true });
}
