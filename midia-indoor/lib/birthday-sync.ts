import { db } from "./db";
import { emitTvEvent } from "./events";
import { fetchEligibleBirthdays } from "./nextfit";

export async function syncNextfitBirthdays(adminUserId?: string) {
  const records = await fetchEligibleBirthdays();
  let created = 0;
  let updated = 0;

  for (const row of records) {
    const existing = await db.birthday.findFirst({ where: { externalSource: "NEXTFIT", externalId: row.externalId } });
    if (existing) {
      await db.birthday.update({ where: { id: existing.id }, data: { name: row.name, birthDate: row.birthDate, photoUrl: row.photoUrl, showLastName: true, active: true } });
      updated += 1;
    } else {
      await db.birthday.create({ data: { ...row, externalSource: "NEXTFIT", showLastName: true, active: true } });
      created += 1;
    }
  }

  await db.auditLog.create({
    data: {
      adminUserId,
      action: adminUserId ? "SYNC_NEXTFIT" : "SYNC_NEXTFIT_AUTO",
      entity: "Birthday",
      details: { created, updated, total: records.length },
    },
  });
  emitTvEvent({ type: "playlist.reload" });
  return { created, updated, total: records.length };
}
