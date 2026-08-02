import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  findFirst: vi.fn(),
  update: vi.fn(),
  create: vi.fn(),
  auditCreate: vi.fn(),
  emitTvEvent: vi.fn(),
  fetchEligibleBirthdays: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
  db: {
    birthday: { findFirst: mocks.findFirst, update: mocks.update, create: mocks.create },
    auditLog: { create: mocks.auditCreate },
  },
}));
vi.mock("@/lib/events", () => ({ emitTvEvent: mocks.emitTvEvent }));
vi.mock("@/lib/nextfit", () => ({ fetchEligibleBirthdays: mocks.fetchEligibleBirthdays }));

import { syncNextfitBirthdays } from "@/lib/birthday-sync";

describe("sincronização de aniversariantes do NextFit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.update.mockResolvedValue({});
    mocks.create.mockResolvedValue({});
    mocks.auditCreate.mockResolvedValue({});
  });

  it("habilita nome e sobrenome ao criar e atualizar aniversariantes", async () => {
    const records = [
      { externalId: "1", name: "Fabiana Silva", birthDate: new Date("1990-08-02T12:00:00Z"), photoUrl: null },
      { externalId: "2", name: "Marina Souza", birthDate: new Date("1992-08-02T12:00:00Z"), photoUrl: null },
    ];
    mocks.fetchEligibleBirthdays.mockResolvedValue(records);
    mocks.findFirst.mockResolvedValueOnce(null).mockResolvedValueOnce({ id: "birthday-2" });

    await syncNextfitBirthdays();

    expect(mocks.create).toHaveBeenCalledWith({
      data: expect.objectContaining({ externalId: "1", showLastName: true }),
    });
    expect(mocks.update).toHaveBeenCalledWith({
      where: { id: "birthday-2" },
      data: expect.objectContaining({ name: "Marina Souza", showLastName: true }),
    });
  });
});
