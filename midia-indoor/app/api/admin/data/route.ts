import { NextResponse } from "next/server";
import { adminOrUnauthorized } from "@/lib/auth-api";
import { db } from "@/lib/db";
import { getSettings } from "@/lib/settings";

export async function GET() {
  const auth = await adminOrUnauthorized(); if ("response" in auth) return auth.response;
  const now = new Date(); const settings = await getSettings(); const stale = new Date(now.getTime() - 45_000);
  await db.displayDevice.updateMany({ where: { lastSeenAt: { lt: stale } }, data: { status: "OFFLINE" } });
  const [media, birthdays, queue, lastEntry, devices, activeMedia] = await Promise.all([
    db.sponsorMedia.findMany({ orderBy: [{ sortOrder: "asc" }, { createdAt: "desc" }] }),
    db.birthday.findMany({ orderBy: { name: "asc" } }),
    db.welcomeQueue.findMany({ where: { status: { in: ["PENDING", "DISPLAYING"] }, expiresAt: { gt: now } }, orderBy: { createdAt: "asc" } }),
    db.entryEvent.findFirst({ where: { duplicate: false }, orderBy: { enteredAt: "desc" } }),
    db.displayDevice.findMany({ orderBy: { name: "asc" } }),
    db.sponsorMedia.count({ where: { active: true } }),
  ]);
  const today = new Intl.DateTimeFormat("en-US", { month: "numeric", day: "numeric", timeZone: settings.timezone }).format(now);
  const birthdaysToday = birthdays.filter((item) => new Intl.DateTimeFormat("en-US", { month: "numeric", day: "numeric", timeZone: "UTC" }).format(item.birthDate) === today).length;
  const safeSettings = Object.fromEntries(Object.entries(settings).filter(([key]) => !["tvTokenHash", "entryApiKeyHash"].includes(key)));
  return NextResponse.json({ media, birthdays, queue, lastEntry, devices, settings: safeSettings, metrics: { activeMedia, birthdaysToday, queueSize: queue.length, onlineDevices: devices.filter((device) => device.status === "ONLINE").length } });
}
