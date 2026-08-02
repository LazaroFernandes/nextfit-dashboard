import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { safeUploadFilename, uploadMimeType } from "@/lib/upload-file";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(_request: Request, { params }: { params: Promise<{ filename: string }> }) {
  const requested = decodeURIComponent((await params).filename);
  const filename = safeUploadFilename(requested);
  const mimeType = filename && uploadMimeType(filename);
  if (!filename || !mimeType) return NextResponse.json({ error: "Arquivo inválido" }, { status: 400 });

  try {
    const file = await readFile(path.join(process.cwd(), "public", "uploads", filename));
    return new Response(new Uint8Array(file), {
      headers: {
        "Content-Type": mimeType,
        "Content-Length": String(file.byteLength),
        "Cache-Control": "public, max-age=3600, immutable",
        "Content-Disposition": `inline; filename="${filename}"`,
      },
    });
  } catch {
    return NextResponse.json({ error: "Arquivo não encontrado" }, { status: 404 });
  }
}
