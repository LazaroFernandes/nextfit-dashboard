import TvScreen from "@/components/TvScreen";
import { validateTvToken } from "@/lib/settings";
import { loadTvBootstrap } from "@/lib/tv-bootstrap";

export const dynamic = "force-dynamic";

export default async function TvPage({ searchParams }: { searchParams: Promise<{ token?: string; device?: string }> }) {
  const params = await searchParams;
  const token = params.token || "";
  const device = params.device || "tv-principal";
  const legacyReload = <script dangerouslySetInnerHTML={{ __html: "window.__ctivLegacyReload=window.setTimeout(function(){window.location.reload();},5000);" }} />;
  if (!(await validateTvToken(token))) return <>{legacyReload}<TvScreen token={token} device={device} initialData={null} initialError="Token de exibição inválido" /></>;
  return <>{legacyReload}<TvScreen token={token} device={device} initialData={await loadTvBootstrap(device)} /></>;
}
