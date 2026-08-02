import { describe, expect, it } from "vitest";
import { settingsSchema } from "@/lib/schemas";

const settings = {
  welcomeDurationSec: 15,
  birthdayDurationSec: 8,
  duplicateWindowMin: 10,
  defaultWelcomeMessage: "Seja bem-vindo, {nome}!",
  alternateMessages: [],
  randomMessages: false,
  fallbackTitle: "CT Italo Vieira",
  fallbackSubtitle: "Forca. Movimento. Evolucao.",
  timezone: "America/Sao_Paulo",
  unitId: "ct-italo-vieira",
  showClock: true,
  maxQueueSize: 50,
  eventTtlMin: 30,
  reducedDurationThreshold: 8,
  reducedDurationSec: 8,
  entryApiKey: "",
};

describe("token da TV", () => {
  it("aceita token com qualquer quantidade de caracteres", () => {
    expect(settingsSchema.safeParse({ ...settings, tvToken: "x" }).success).toBe(true);
  });

  it("mantem o token atual quando o campo fica vazio", () => {
    expect(settingsSchema.safeParse({ ...settings, tvToken: "" }).success).toBe(true);
  });
});
