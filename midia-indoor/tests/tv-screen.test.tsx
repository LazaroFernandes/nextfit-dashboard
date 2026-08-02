import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import TvScreen from "@/components/TvScreen";
import type { TvBootstrapData } from "@/lib/tv-bootstrap";

const data: TvBootstrapData = {
  media: [{ id: "media-1", name: "Arte PNG", fileUrl: "/uploads/arte.png", type: "IMAGE", durationSec: 10, sponsorName: null }],
  birthdays: [{ id: "birthday-1", name: "Aluno Aniversariante", photoUrl: null, message: "Feliz aniversário!", showLastName: false }],
  queue: [{ id: "queue-1", displayName: "Maria", message: "Seja bem-vinda, Maria!", createdAt: new Date().toISOString() }],
  settings: { welcomeDurationSec: 15, birthdayDurationSec: 8, fallbackTitle: "CT Italo Vieira", fallbackSubtitle: "Forca. Movimento. Evolucao.", logoUrl: "/demo/logo-ct.svg", showClock: true, timezone: "America/Sao_Paulo", reducedDurationThreshold: 8, reducedDurationSec: 8 },
  paused: false,
};

describe("tela compatível da TV", () => {
  it("entrega mídia, aniversário e entrada no HTML inicial", () => {
    const html = renderToStaticMarkup(<TvScreen token="ctiv" device="tv-teste" initialData={data} />);
    expect(html).toContain("/uploads/arte.png");
    expect(html).toContain("Aluno");
    expect(html).toContain("Seja bem-vinda, Maria!");
  });
});
