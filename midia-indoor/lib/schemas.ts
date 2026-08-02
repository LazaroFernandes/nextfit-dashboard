import { z } from "zod";

export const entrySchema = z.object({
  studentId: z.string().trim().min(1).max(100),
  name: z.string().trim().min(2).max(120),
  enteredAt: z.iso.datetime({ offset: true }),
  unitId: z.string().trim().min(1).max(80),
});

export const birthdaySchema = z.object({
  id: z.string().optional(),
  name: z.string().trim().min(2).max(120),
  birthDate: z.string().min(10),
  photoUrl: z.string().trim().max(500).optional().or(z.literal("")),
  message: z.string().trim().max(180).optional().or(z.literal("")),
  showLastName: z.boolean().default(false),
  active: z.boolean().default(true),
});

export const settingsSchema = z.object({
  welcomeDurationSec: z.coerce.number().int().min(3).max(60),
  birthdayDurationSec: z.coerce.number().int().min(3).max(60),
  duplicateWindowMin: z.coerce.number().int().min(1).max(1440),
  defaultWelcomeMessage: z.string().trim().min(3).max(120).refine((v) => v.includes("{nome}"), "Inclua {nome}"),
  alternateMessages: z.array(z.string().trim().min(3).max(120)),
  randomMessages: z.boolean(),
  fallbackTitle: z.string().trim().min(2).max(80),
  fallbackSubtitle: z.string().trim().min(2).max(140),
  timezone: z.string().trim().min(3).max(80),
  unitId: z.string().trim().min(1).max(80),
  showClock: z.boolean(),
  maxQueueSize: z.coerce.number().int().min(1).max(500),
  eventTtlMin: z.coerce.number().int().min(1).max(1440),
  reducedDurationThreshold: z.coerce.number().int().min(1).max(100),
  reducedDurationSec: z.coerce.number().int().min(3).max(30),
  tvToken: z.string().trim().optional(),
  entryApiKey: z.string().min(16).optional().or(z.literal("")),
});
