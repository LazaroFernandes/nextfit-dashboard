import { NextResponse } from "next/server";
import { adminOrUnauthorized } from "@/lib/auth-api";
import { syncNextfitBirthdays } from "@/lib/birthday-sync";

export async function POST() {
  const auth = await adminOrUnauthorized();
  if ("response" in auth) return auth.response;
  try {
    return NextResponse.json(await syncNextfitBirthdays(auth.session.sub));
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Falha na sincronização" }, { status: 502 });
  }
}
