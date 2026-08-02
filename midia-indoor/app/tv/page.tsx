import TvScreen from "@/components/TvScreen";
import { validateTvToken } from "@/lib/settings";
import { loadTvBootstrap } from "@/lib/tv-bootstrap";

export const dynamic = "force-dynamic";

export default async function TvPage({ searchParams }: { searchParams: Promise<{ token?: string; device?: string }> }) {
  const params = await searchParams;
  const token = params.token || "";
  const device = params.device || "tv-principal";
  if (!(await validateTvToken(token))) return <TvScreen token={token} device={device} initialData={null} initialError="Token de exibição inválido" />;
  const data = await loadTvBootstrap(device);
  const welcome = data.queue[0];
  const duration = welcome && data.queue.length >= data.settings.reducedDurationThreshold ? data.settings.reducedDurationSec : data.settings.welcomeDurationSec;
  const target = welcome ? `/api/tv/legacy-complete?token=${encodeURIComponent(token)}&device=${encodeURIComponent(device)}&id=${encodeURIComponent(welcome.id)}` : `/tv?token=${encodeURIComponent(token)}&device=${encodeURIComponent(device)}`;
  const delay = welcome ? duration * 1000 : 5000;
  const legacyReload = <script dangerouslySetInnerHTML={{ __html: `window.__ctivLegacyReload=window.setTimeout(function(){window.location.replace(${JSON.stringify(target)});},${delay});` }} />;
  return <>{legacyReload}<TvScreen token={token} device={device} initialData={data} /></>;
}
