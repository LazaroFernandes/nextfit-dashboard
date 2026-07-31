import { NextRequest, NextResponse } from "next/server";
import { adminOrUnauthorized } from "@/lib/auth-api";
import { db } from "@/lib/db";
import { emitTvEvent } from "@/lib/events";
import { settingsSchema } from "@/lib/schemas";
import { hashSecret } from "@/lib/security";

export async function PATCH(request: NextRequest) { const auth = await adminOrUnauthorized(); if ("response" in auth) return auth.response; const parsed = settingsSchema.safeParse(await request.json()); if (!parsed.success) return NextResponse.json({ error: "Configurações inválidas", details: parsed.error.flatten() }, { status: 400 }); const { tvToken, entryApiKey, ...values } = parsed.data; const settings = await db.systemSettings.update({ where: { id: "default" }, data: { ...values, alternateMessages: values.alternateMessages, ...(tvToken ? { tvTokenHash: hashSecret(tvToken) } : {}), ...(entryApiKey ? { entryApiKeyHash: hashSecret(entryApiKey) } : {}) } }); await db.auditLog.create({ data: { adminUserId: auth.session.sub, action: "UPDATE", entity: "SystemSettings", entityId: "default" } }); emitTvEvent({ type: "playlist.reload" }); const safe = Object.fromEntries(Object.entries(settings).filter(([key]) => !["tvTokenHash", "entryApiKeyHash"].includes(key))); return NextResponse.json(safe); }
