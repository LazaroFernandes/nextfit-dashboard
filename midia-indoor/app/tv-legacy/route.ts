import { NextRequest } from "next/server";
import { renderLegacyTvHtml } from "@/lib/legacy-tv";
import { validateTvToken } from "@/lib/settings";
import { loadTvBootstrap } from "@/lib/tv-bootstrap";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token") || "";
  const device = request.nextUrl.searchParams.get("device") || "tv-principal";
  if (!(await validateTvToken(token))) {
    return new Response("<!doctype html><html><body style=\"background:#030814;color:white;font-family:Arial;padding:40px\"><h1>Token de exibição inválido</h1></body></html>", {
      status: 401,
      headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
    });
  }
  const data = await loadTvBootstrap(device);
  return new Response(renderLegacyTvHtml(data, token, device), {
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store, max-age=0" },
  });
}
