import TvScreen from "@/components/TvScreen";

export default async function TvPage({ searchParams }: { searchParams: Promise<{ token?: string; device?: string }> }) {
  const params = await searchParams;
  return <TvScreen token={params.token || ""} device={params.device || "tv-principal"} />;
}
