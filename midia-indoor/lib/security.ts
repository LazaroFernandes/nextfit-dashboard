import { createHash, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SignJWT, jwtVerify } from "jose";

const COOKIE_NAME = "ctiv_admin_session";
const secret = () => new TextEncoder().encode(process.env.AUTH_SECRET || "dev-only-change-me-at-least-32-characters");

export type Session = { sub: string; email: string; name: string };

export async function createSession(session: Session) {
  const token = await new SignJWT({ email: session.email, name: session.name })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(session.sub)
    .setIssuedAt()
    .setExpirationTime("12h")
    .sign(secret());
  const jar = await cookies();
  jar.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 12,
  });
}

export async function clearSession() {
  const jar = await cookies();
  jar.delete(COOKIE_NAME);
}

export async function getSession(): Promise<Session | null> {
  const token = (await cookies()).get(COOKIE_NAME)?.value;
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, secret());
    if (!payload.sub || typeof payload.email !== "string" || typeof payload.name !== "string") return null;
    return { sub: payload.sub, email: payload.email, name: payload.name };
  } catch {
    return null;
  }
}

export async function requireAdmin() {
  const session = await getSession();
  if (!session) redirect("/login");
  return session;
}

export function hashSecret(value: string) {
  return createHash("sha256").update(value).digest("hex");
}

export function safeSecretEqual(provided: string | null | undefined, expected: string | null | undefined) {
  if (!provided || !expected) return false;
  const a = Buffer.from(hashSecret(provided));
  const b = Buffer.from(expected.length === 64 ? expected : hashSecret(expected));
  return a.length === b.length && timingSafeEqual(a, b);
}
