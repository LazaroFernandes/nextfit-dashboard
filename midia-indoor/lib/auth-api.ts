import { NextResponse } from "next/server";
import { getSession } from "./security";

export async function adminOrUnauthorized() {
  const session = await getSession();
  return session ? { session } : { response: NextResponse.json({ error: "Não autorizado" }, { status: 401 }) };
}
