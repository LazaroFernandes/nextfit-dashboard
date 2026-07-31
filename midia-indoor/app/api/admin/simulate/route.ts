import { NextRequest, NextResponse } from "next/server";
import { adminOrUnauthorized } from "@/lib/auth-api";
import { db } from "@/lib/db";
import { emitTvEvent } from "@/lib/events";
import { getSettings } from "@/lib/settings";
import { chooseWelcomeMessage, firstName, sanitizeDisplayName } from "@/lib/welcome";
import { z } from "zod";

const schema = z.object({ name: z.string().trim().min(2).max(120) });
export async function POST(request: NextRequest) { const auth = await adminOrUnauthorized(); if ("response" in auth) return auth.response; const parsed = schema.safeParse(await request.json()); if (!parsed.success) return NextResponse.json({ error: "Nome inválido" }, { status: 400 }); const settings = await getSettings(); const name = sanitizeDisplayName(parsed.data.name); const alternatives = Array.isArray(settings.alternateMessages) ? settings.alternateMessages.filter((v): v is string => typeof v === "string") : []; const event = await db.entryEvent.create({ data: { externalId: `admin-${Date.now()}`, studentName: name, enteredAt: new Date(), unitId: settings.unitId, source: "ADMIN" } }); const queue = await db.welcomeQueue.create({ data: { entryEventId: event.id, displayName: firstName(name), message: chooseWelcomeMessage(name, settings.defaultWelcomeMessage, alternatives, settings.randomMessages), expiresAt: new Date(Date.now() + settings.eventTtlMin * 60_000), priority: 10 } }); await db.auditLog.create({ data: { adminUserId: auth.session.sub, action: "SIMULATE_ENTRY", entity: "EntryEvent", entityId: event.id, details: { name } } }); emitTvEvent({ type: "welcome", payload: queue }); return NextResponse.json(queue, { status: 201 }); }
