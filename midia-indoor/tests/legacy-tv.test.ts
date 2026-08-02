import { describe, expect, it } from "vitest";
import { renderLegacyTvHtml } from "@/lib/legacy-tv";
import type { TvBootstrapData } from "@/lib/tv-bootstrap";

const data: TvBootstrapData = {
  media: [{ id: "m1", name: "Logo", fileUrl: "/uploads/logo.png", type: "IMAGE", durationSec: 10, sponsorName: null }],
  birthdays: [{ id: "b1", name: "Ítalo Vieira", photoUrl: "/uploads/italo.png", message: "Feliz aniversário!", showLastName: true }],
  queue: [{ id: "q1", displayName: "Maria Silva", message: "Bom treino!", createdAt: "2026-08-01T12:00:00.000Z" }],
  settings: { welcomeDurationSec: 8, birthdayDurationSec: 10, fallbackTitle: "Bem-vindo", fallbackSubtitle: "Bom treino", logoUrl: "", showClock: true, timezone: "America/Sao_Paulo", reducedDurationThreshold: 4, reducedDurationSec: 4 },
  paused: false,
};

describe("legacy TV renderer", () => {
  it("server-renders media, birthday and welcome content", () => {
    const html = renderLegacyTvHtml(data, "ctiv", "tv-principal");
    expect(html).toContain("/uploads/logo.png");
    expect(html).toContain("Ítalo Vieira");
    expect(html).toContain("Maria Silva");
    expect(html).toContain("Bom treino!");
  });

  it("uses old-browser primitives", () => {
    const html = renderLegacyTvHtml(data, "ctiv", "tv-principal");
    expect(html).toContain("new XMLHttpRequest()");
    expect(html).toContain("display:table");
    expect(html).not.toContain("display:grid");
    expect(html).not.toContain("display:flex");
    expect(html).not.toContain("EventSource");
    expect(html).not.toContain("fetch(");
    expect(html).not.toContain("=>");
    expect(html).toContain("renderMedia();renderAll();clock();");
  });
});
