import { describe, expect, it } from "vitest";
import { safeUploadFilename, uploadMimeType } from "@/lib/upload-file";

describe("arquivos enviados", () => {
  it("entrega PNG com o tipo correto", () => {
    expect(uploadMimeType("arte.PNG")).toBe("image/png");
  });

  it("aceita os formatos cadastrados na playlist", () => {
    expect(uploadMimeType("foto.jpg")).toBe("image/jpeg");
    expect(uploadMimeType("video.mp4")).toBe("video/mp4");
  });

  it("bloqueia caminhos fora da pasta de uploads", () => {
    expect(safeUploadFilename("../segredo.png")).toBeNull();
  });
});
