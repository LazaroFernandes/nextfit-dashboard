import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { getSettings, validateTvToken } from "@/lib/settings";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  if (!(await validateTvToken(token))) return NextResponse.json({ error: "Token inválido" }, { status: 401 });
  const deviceName = request.nextUrl.searchParams.get("device") || "tv-principal";
  const settings = await getSettings();
  const now = new Date();
  await db.welcomeQueue.updateMany({ where: { status: { in: ["PENDING", "DISPLAYING"] }, expiresAt: { lt: now } }, data: { status: "EXPIRED" } });
  const [media, birthdaysRaw, queue, device] = await Promise.all([
    db.sponsorMedia.findMany({ where: { active: true, AND: [{ OR: [{ startsAt: null }, { startsAt: { lte: now } }] }, { OR: [{ endsAt: null }, { endsAt: { gte: now } }] }] }, orderBy: [{ priority: "desc" }, { sortOrder: "asc" }] }),
    db.birthday.findMany({ where: { active: true }, orderBy: { name: "asc" } }),
    db.welcomeQueue.findMany({ where: { status: { in: ["PENDING", "DISPLAYING"] }, expiresAt: { gt: now } }, orderBy: [{ priority: "desc" }, { createdAt: "asc" }], take: settings.maxQueueSize }),
    db.displayDevice.upsert({ where: { name: deviceName }, create: { name: deviceName, unitId: settings.unitId, status: "ONLINE", lastSeenAt: now }, update: { status: "ONLINE", lastSeenAt: now } }),
  ]);
  const birthdayParts = localDateParts(now, settings.timezone);
  const birthdays = birthdaysRaw.filter((item) => {
    const parts = localDateParts(item.birthDate, "UTC");
    return parts.month === birthdayParts.month && parts.day === birthdayParts.day;
  });
  return NextResponse.json({ media, birthdays, queue, settings: publicSettings(settings), paused: device.paused });
}

function localDateParts(date: Date, timeZone: string) {
  const parts = new Intl.DateTimeFormat("en-US", { day: "numeric", month: "numeric", timeZone }).formatToParts(date);
  return { day: Number(parts.find((p) => p.type === "day")?.value), month: Number(parts.find((p) => p.type === "month")?.value) };
}

function publicSettings(settings: Awaited<ReturnType<typeof getSettings>>) {
  return Object.fromEntries(Object.entries(settings).filter(([key]) => !["tvTokenHash", "entryApiKeyHash"].includes(key)));
}
