import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { emitTvEvent } from "@/lib/events";
import { allowRequest } from "@/lib/rate-limit";
import { entrySchema } from "@/lib/schemas";
import { getSettings, validateEntryKey } from "@/lib/settings";
import { chooseWelcomeMessage, sanitizeDisplayName } from "@/lib/welcome";

export async function POST(request: NextRequest) {
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0] || "unknown";
  if (!allowRequest(ip)) return NextResponse.json({ error: "Limite de requisições excedido" }, { status: 429 });
  if (!(await validateEntryKey(request.headers.get("x-api-key")))) return NextResponse.json({ error: "API Key inválida" }, { status: 401 });
  const parsed = entrySchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "Payload inválido", details: parsed.error.flatten() }, { status: 400 });
  const settings = await getSettings();
  if (parsed.data.unitId !== settings.unitId) return NextResponse.json({ error: "Unidade não autorizada" }, { status: 403 });
  const enteredAt = new Date(parsed.data.enteredAt);
  const clockDelta = enteredAt.getTime() - Date.now();
  if (clockDelta > 5 * 60_000 || clockDelta < -settings.eventTtlMin * 60_000) return NextResponse.json({ error: "Evento fora da janela de validade" }, { status: 422 });
  const duplicateSince = new Date(enteredAt.getTime() - settings.duplicateWindowMin * 60_000);
  const duplicate = await db.entryEvent.findFirst({ where: { externalId: parsed.data.studentId, duplicate: false, enteredAt: { gte: duplicateSince } }, orderBy: { enteredAt: "desc" } });
  if (duplicate) {
    await db.entryEvent.create({ data: { externalId: parsed.data.studentId, studentName: sanitizeDisplayName(parsed.data.name), enteredAt, unitId: parsed.data.unitId, duplicate: true, rawPayload: parsed.data } });
    return NextResponse.json({ status: "duplicate", message: "Evento ignorado dentro da janela de duplicidade", duplicateOf: duplicate.id }, { status: 202 });
  }
  const activeQueue = await db.welcomeQueue.count({ where: { status: { in: ["PENDING", "DISPLAYING"] }, expiresAt: { gt: new Date() } } });
  if (activeQueue >= settings.maxQueueSize) return NextResponse.json({ error: "Fila cheia", status: "queue_full" }, { status: 503 });
  const alternatives = Array.isArray(settings.alternateMessages) ? settings.alternateMessages.filter((value): value is string => typeof value === "string") : [];
  const cleanName = sanitizeDisplayName(parsed.data.name);
  const result = await db.$transaction(async (tx) => {
    const student = await tx.student.upsert({ where: { externalId: parsed.data.studentId }, create: { externalId: parsed.data.studentId, name: cleanName, source: "TURNSTILE" }, update: { name: cleanName, active: true } });
    const event = await tx.entryEvent.create({ data: { studentId: student.id, externalId: parsed.data.studentId, studentName: cleanName, enteredAt, unitId: parsed.data.unitId, rawPayload: parsed.data } });
    const queue = await tx.welcomeQueue.create({ data: { entryEventId: event.id, displayName: cleanName, message: chooseWelcomeMessage(cleanName, settings.defaultWelcomeMessage, alternatives, settings.randomMessages), expiresAt: new Date(enteredAt.getTime() + settings.eventTtlMin * 60_000) } });
    return { event, queue };
  });
  emitTvEvent({ type: "welcome", payload: result.queue });
  return NextResponse.json({ status: "queued", eventId: result.event.id, queueId: result.queue.id, message: result.queue.message }, { status: 201 });
}
