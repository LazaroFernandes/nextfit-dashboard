import { NextRequest, NextResponse } from "next/server";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { adminOrUnauthorized } from "@/lib/auth-api";
import { db } from "@/lib/db";
import { emitTvEvent } from "@/lib/events";

const allowed = new Set(["image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"]);
export async function POST(request: NextRequest) {
  const auth = await adminOrUnauthorized(); if ("response" in auth) return auth.response;
  const form = await request.formData(); const file = form.get("file");
  if (!(file instanceof File) || !allowed.has(file.type)) return NextResponse.json({ error: "Arquivo inválido. Use JPG, PNG, WEBP, MP4 ou WEBM." }, { status: 400 });
  const maxBytes = Number(process.env.UPLOAD_MAX_MB || 100) * 1024 * 1024;
  if (file.size > maxBytes) return NextResponse.json({ error: "Arquivo acima do limite configurado." }, { status: 413 });
  const ext = mimeExtension(file.type); const filename = `${randomUUID()}.${ext}`; const uploadDir = path.join(process.cwd(), "public", "uploads");
  await mkdir(uploadDir, { recursive: true }); await writeFile(path.join(uploadDir, filename), Buffer.from(await file.arrayBuffer()));
  const item = await db.sponsorMedia.create({ data: { name: clean(String(form.get("name") || file.name), 100), fileUrl: `/uploads/${filename}`, type: file.type.startsWith("video/") ? "VIDEO" : "IMAGE", mimeType: file.type, durationSec: clamp(form.get("durationSec"), 3, 300, 10), sortOrder: clamp(form.get("sortOrder"), 0, 9999, 0), priority: clamp(form.get("priority"), 0, 100, 0), sponsorName: clean(String(form.get("sponsorName") || ""), 100) || null, startsAt: form.get("startsAt") ? new Date(String(form.get("startsAt"))) : null, endsAt: form.get("endsAt") ? new Date(String(form.get("endsAt"))) : null } });
  await db.auditLog.create({ data: { adminUserId: auth.session.sub, action: "CREATE", entity: "SponsorMedia", entityId: item.id, details: { name: item.name } } }); emitTvEvent({ type: "playlist.reload" });
  return NextResponse.json(item, { status: 201 });
}
function mimeExtension(mime: string) { return ({ "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "video/mp4": "mp4", "video/webm": "webm" } as Record<string,string>)[mime]; }
function clamp(value: FormDataEntryValue | null, min: number, max: number, fallback: number) { const number = Number(value); return Number.isFinite(number) ? Math.min(max, Math.max(min, Math.round(number))) : fallback; }
function clean(value: string, length: number) { return value.replace(/[<>]/g, "").trim().slice(0, length); }
