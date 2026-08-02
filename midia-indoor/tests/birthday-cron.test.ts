import { afterEach, describe, expect, it, vi } from "vitest";
import { isBirthdayCronAuthorized } from "@/app/api/cron/birthdays/route";
import { fetchEligibleBirthdays } from "@/lib/nextfit";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  delete process.env.NEXTFIT_API_KEY;
  delete process.env.NEXTFIT_BASE_URL;
});

describe("sincronização automática de aniversários", () => {
  it("aceita somente a chave interna configurada", () => {
    expect(isBirthdayCronAuthorized("chave-interna", "chave-interna")).toBe(true);
    expect(isBirthdayCronAuthorized("chave-errada", "chave-interna")).toBe(false);
  });

  it("recusa quando a chave não foi configurada", () => {
    expect(isBirthdayCronAuthorized(null, undefined)).toBe(false);
  });

  it("importa apenas aniversariantes elegíveis do dia", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-01T12:00:00-03:00"));
    process.env.NEXTFIT_API_KEY = "key";
    process.env.NEXTFIT_BASE_URL = "https://nextfit.test";
    vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify({
      items: url.includes("GetClientes")
        ? [{ id: 1, nome: "Ana", dataNascimento: "1990-08-01T00:00:00", inativo: false }, { id: 2, nome: "Bia", dataNascimento: "1990-08-02T00:00:00", inativo: false }]
        : [{ codigoCliente: 1, status: "Ativo" }, { codigoCliente: 2, status: "Ativo" }],
      temProximaPagina: false,
    }), { status: 200 })));

    const records = await fetchEligibleBirthdays();
    expect(records.map((item) => item.name)).toEqual(["Ana"]);
  });
});
