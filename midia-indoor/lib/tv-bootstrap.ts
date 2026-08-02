import { db } from "./db";
import { getSettings } from "./settings";

export type TvBootstrapData = {
  media: Array<{ id: string; name: string; fileUrl: string; type: "IMAGE" | "VIDEO"; durationSec: number; sponsorName: string | null }>;
  birthdays: Array<{ id: string; name: string; photoUrl: string | null; message: string | null; showLastName: boolean }>;
  queue: Array<{ id: string; displayName: string; message: string; createdAt: string }>;
  settings: {
    welcomeDurationSec: number;
    birthdayDurationSec: number;
    fallbackTitle: string;
    fallbackSubtitle: string;
    logoUrl: string;
    showClock: boolean;
    timezone: string;
    reducedDurationThreshold: number;
    reducedDurationSec: number;
  };
  paused: boolean;
};

export async function loadTvBootstrap(deviceName: string): Promise<TvBootstrapData> {
  const settings = await getSettings();
  const now = new Date();
  await db.welcomeQueue.updateMany({ where: { status: { in: ["PENDING", "DISPLAYING"] }, expiresAt: { lt: now } }, data: { status: "EXPIRED" } });
  const [media, birthdaysRaw, queue, device] = await Promise.all([
    db.sponsorMedia.findMany({ where: { active: true, AND: [{ OR: [{ startsAt: null }, { startsAt: { lte: now } }] }, { OR: [{ endsAt: null }, { endsAt: { gte: now } }] }] }, orderBy: [{ priority: "desc" }, { sortOrder: "asc" }], select: { id: true, name: true, fileUrl: true, type: true, durationSec: true, sponsorName: true } }),
    db.birthday.findMany({ where: { active: true }, orderBy: { name: "asc" }, select: { id: true, name: true, birthDate: true, photoUrl: true, message: true, showLastName: true } }),
    db.welcomeQueue.findMany({ where: { status: { in: ["PENDING", "DISPLAYING"] }, expiresAt: { gt: now } }, orderBy: [{ priority: "desc" }, { createdAt: "asc" }], take: settings.maxQueueSize, select: { id: true, displayName: true, message: true, createdAt: true } }),
    db.displayDevice.upsert({ where: { name: deviceName }, create: { name: deviceName, unitId: settings.unitId, status: "ONLINE", lastSeenAt: now }, update: { status: "ONLINE", lastSeenAt: now } }),
  ]);
  const birthdayParts = localDateParts(now, settings.timezone);
  const birthdays = birthdaysRaw.filter((item) => {
    const parts = localDateParts(item.birthDate, "UTC");
    return parts.month === birthdayParts.month && parts.day === birthdayParts.day;
  }).map(({ birthDate: _birthDate, ...birthday }) => birthday);

  return {
    media,
    birthdays,
    queue: queue.map((item) => ({ ...item, createdAt: item.createdAt.toISOString() })),
    settings: {
      welcomeDurationSec: settings.welcomeDurationSec,
      birthdayDurationSec: settings.birthdayDurationSec,
      fallbackTitle: settings.fallbackTitle,
      fallbackSubtitle: settings.fallbackSubtitle,
      logoUrl: settings.logoUrl,
      showClock: settings.showClock,
      timezone: settings.timezone,
      reducedDurationThreshold: settings.reducedDurationThreshold,
      reducedDurationSec: settings.reducedDurationSec,
    },
    paused: device.paused,
  };
}

function localDateParts(date: Date, timeZone: string) {
  const parts = new Intl.DateTimeFormat("en-US", { day: "numeric", month: "numeric", timeZone }).formatToParts(date);
  return { day: Number(parts.find((part) => part.type === "day")?.value), month: Number(parts.find((part) => part.type === "month")?.value) };
}
