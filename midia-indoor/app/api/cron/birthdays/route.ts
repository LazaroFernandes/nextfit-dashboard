import { NextRequest, NextResponse } from "next/server";
import { syncNextfitBirthdays } from "@/lib/birthday-sync";
import { safeSecretEqual } from "@/lib/security";

export const dynamic = "force-dynamic";

export function isBirthdayCronAuthorized(provided: string | null, expected: string | undefined) {
  return safeSecretEqual(provided, expected);
}

export async function POST(request: NextRequest) {
  if (!isBirthdayCronAuthorized(request.headers.get("x-api-key"), process.env.ENTRY_API_KEY)) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }
  try {
    return NextResponse.json(await syncNextfitBirthdays());
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Falha na sincronização" }, { status: 502 });
  }
}
