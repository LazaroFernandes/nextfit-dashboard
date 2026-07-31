import { db } from "./db";
import { hashSecret, safeSecretEqual } from "./security";

export async function getSettings() {
  return db.systemSettings.upsert({
    where: { id: "default" },
    update: {},
    create: {
      id: "default",
      tvTokenHash: process.env.TV_DISPLAY_TOKEN ? hashSecret(process.env.TV_DISPLAY_TOKEN) : null,
      entryApiKeyHash: process.env.ENTRY_API_KEY ? hashSecret(process.env.ENTRY_API_KEY) : null,
    },
  });
}

export async function validateTvToken(token: string | null) {
  const settings = await getSettings();
  return safeSecretEqual(token, settings.tvTokenHash || process.env.TV_DISPLAY_TOKEN);
}

export async function validateEntryKey(key: string | null) {
  const settings = await getSettings();
  return safeSecretEqual(key, settings.entryApiKeyHash || process.env.ENTRY_API_KEY);
}
