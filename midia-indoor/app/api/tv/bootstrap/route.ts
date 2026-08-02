import { NextRequest, NextResponse } from "next/server";
import { validateTvToken } from "@/lib/settings";
import { loadTvBootstrap } from "@/lib/tv-bootstrap";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  if (!(await validateTvToken(token))) return NextResponse.json({ error: "Token inválido" }, { status: 401 });
  const deviceName = request.nextUrl.searchParams.get("device") || "tv-principal";
  return NextResponse.json(await loadTvBootstrap(deviceName));
}
