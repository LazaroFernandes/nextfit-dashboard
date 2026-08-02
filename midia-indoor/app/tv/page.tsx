import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function TvPage({ searchParams }: { searchParams: Promise<{ token?: string; device?: string }> }) {
  const params = await searchParams;
  const token = params.token || "";
  const device = params.device || "tv-principal";
  redirect(`/tv-legacy?token=${encodeURIComponent(token)}&device=${encodeURIComponent(device)}`);
}
