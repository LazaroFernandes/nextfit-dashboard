"use client";
/* eslint-disable @next/next/no-img-element */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Media = { id: string; name: string; fileUrl: string; type: "IMAGE" | "VIDEO"; durationSec: number; sponsorName?: string | null };
type Birthday = { id: string; name: string; photoUrl?: string | null; message?: string | null; showLastName: boolean };
type QueueItem = { id: string; displayName: string; message: string; createdAt: string };
type Settings = { welcomeDurationSec: number; birthdayDurationSec: number; fallbackTitle: string; fallbackSubtitle: string; logoUrl: string; showClock: boolean; timezone: string; reducedDurationThreshold: number; reducedDurationSec: number };
type Bootstrap = { media: Media[]; birthdays: Birthday[]; queue: QueueItem[]; settings: Settings; paused: boolean };

const CACHE_KEY = "ctiv-tv-bootstrap-v1";

export default function TvScreen({ token, device }: { token: string; device: string }) {
  const [data, setData] = useState<Bootstrap | null>(null);
  const [mediaIndex, setMediaIndex] = useState(0);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [welcome, setWelcome] = useState<QueueItem | null>(null);
  const [online, setOnline] = useState(false);
  const [error, setError] = useState("");
  const [now, setNow] = useState(new Date());
  const videoRef = useRef<HTMLVideoElement>(null);

  const load = useCallback(async () => {
    try {
      const response = await fetch(`/api/tv/bootstrap?token=${encodeURIComponent(token)}&device=${encodeURIComponent(device)}`, { cache: "no-store" });
      if (!response.ok) throw new Error(response.status === 401 ? "Token de exibição inválido" : "Falha ao carregar a programação");
      const fresh = await response.json() as Bootstrap;
      setData(fresh); setQueue((current) => mergeQueue(current, fresh.queue)); setOnline(true); setError("");
      localStorage.setItem(CACHE_KEY, JSON.stringify(fresh));
    } catch (reason) {
      setOnline(false); setError(reason instanceof Error ? reason.message : "Tela indisponível");
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) { const parsed = JSON.parse(cached) as Bootstrap; setData((current) => current ?? parsed); setQueue((current) => current.length ? current : (parsed.queue || [])); }
    }
  }, [token, device]);

  useEffect(() => { const initial = setTimeout(() => void load(), 0); return () => clearTimeout(initial); }, [load]);
  useEffect(() => { const timer = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(timer); }, []);

  useEffect(() => {
    if (!token) return;
    let retry: ReturnType<typeof setTimeout>;
    let source: EventSource;
    const connect = () => {
      source = new EventSource(`/api/tv/events?token=${encodeURIComponent(token)}&device=${encodeURIComponent(device)}`);
      source.onopen = () => setOnline(true);
      source.onmessage = (event) => {
        const message = JSON.parse(event.data) as { type: string; payload?: QueueItem };
        if (message.type === "welcome" && message.payload) setQueue((current) => mergeQueue(current, [message.payload!]));
        if (message.type === "screen.reload") location.reload();
        if (message.type === "playlist.reload") void load();
        if (message.type === "queue.clear") { setQueue([]); setWelcome(null); }
        if (message.type === "media.pause") setData((current) => current ? { ...current, paused: true } : current);
        if (message.type === "media.resume") setData((current) => current ? { ...current, paused: false } : current);
        if (message.type === "birthday.test" && message.payload) setQueue((current) => current); // event keeps connection active; test data arrives through reload
      };
      source.onerror = () => { setOnline(false); source.close(); retry = setTimeout(connect, 3000); };
    };
    connect();
    return () => { clearTimeout(retry); source?.close(); };
  }, [token, device, load]);

  useEffect(() => {
    const heartbeat = setInterval(() => void fetch(`/api/tv/heartbeat?token=${encodeURIComponent(token)}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ device, currentMedia: data?.media[mediaIndex]?.name || null }) }), 15000);
    return () => clearInterval(heartbeat);
  }, [token, device, data, mediaIndex]);

  const media = useMemo(() => data?.media || [], [data?.media]);
  useEffect(() => {
    if (!media.length || data?.paused) return;
    const current = media[mediaIndex % media.length];
    if (current.type === "VIDEO") return;
    const timer = setTimeout(() => setMediaIndex((index) => (index + 1) % media.length), current.durationSec * 1000);
    return () => clearTimeout(timer);
  }, [media, mediaIndex, data?.paused]);

  useEffect(() => {
    if (!data || welcome || !queue.length) return;
    const activate = setTimeout(() => setWelcome(queue[0]), 0);
    return () => clearTimeout(activate);
  }, [queue, welcome, data]);

  useEffect(() => {
    if (!data || !welcome) return;
    const seconds = queue.length >= data.settings.reducedDurationThreshold ? data.settings.reducedDurationSec : data.settings.welcomeDurationSec;
    const timer = setTimeout(() => {
      setWelcome(null); setQueue((current) => current.filter((item) => item.id !== welcome.id));
      void fetch(`/api/tv/queue?token=${encodeURIComponent(token)}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ id: welcome.id }) });
    }, seconds * 1000);
    return () => clearTimeout(timer);
  }, [queue.length, welcome, data, token]);

  useEffect(() => { if (!videoRef.current) return; if (data?.paused) videoRef.current.pause(); else void videoRef.current.play().catch(() => undefined); }, [data?.paused, mediaIndex]);

  const currentMedia = media[mediaIndex % Math.max(media.length, 1)];
  const dateText = useMemo(() => new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "2-digit", month: "long", timeZone: data?.settings.timezone || "America/Sao_Paulo" }).format(now), [now, data]);
  const timeText = useMemo(() => new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: data?.settings.timezone || "America/Sao_Paulo" }).format(now), [now, data]);

  if (!data) return <main className="grid h-screen place-items-center bg-[#080a0d] text-center"><div><img src="/demo/logo-ct.svg" alt="CT Ítalo Vieira" className="mx-auto mb-7 w-60"/><p className="text-xl text-zinc-400">{error || "Preparando a programação…"}</p></div></main>;

  return <main className="relative h-screen w-screen overflow-hidden bg-[#080a0d] p-[1.4vw]">
    <div className="grid h-full grid-rows-[1fr_auto] gap-[1.2vw]">
      <section className="relative overflow-hidden rounded-[1.3vw] border border-white/10 bg-[#0d1116] shadow-2xl">
        {currentMedia ? <div key={currentMedia.id} className="media-enter h-full w-full">
          {currentMedia.type === "VIDEO" ? <video ref={videoRef} className="h-full w-full object-contain" src={currentMedia.fileUrl} autoPlay={!data.paused} muted playsInline onEnded={() => !data.paused && setMediaIndex((index) => (index + 1) % media.length)} onError={() => setTimeout(() => setMediaIndex((index) => (index + 1) % media.length), 1500)} /> : <img className="h-full w-full object-contain" src={currentMedia.fileUrl} alt={currentMedia.name}/>} 
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,transparent_72%,rgba(0,0,0,.38))]"/>
          {currentMedia.sponsorName && <span className="absolute bottom-[2vw] left-[2vw] text-[1vw] font-semibold uppercase tracking-[.24em] text-white/65">Parceiro · {currentMedia.sponsorName}</span>}
        </div> : <div className="relative h-full"><img src="/demo/institutional.svg" alt="CT Ítalo Vieira" className="h-full w-full object-cover"/><div className="absolute bottom-[5vw] left-[4vw]"><h1 className="text-[4vw] font-black tracking-tight">{data.settings.fallbackTitle}</h1><p className="mt-2 text-[1.5vw] text-white/60">{data.settings.fallbackSubtitle}</p></div></div>}
        {welcome && <div className="welcome-enter absolute bottom-[3vw] left-[3vw] right-[23vw] z-20 overflow-hidden rounded-[1.2vw] border border-blue-300/30 bg-[linear-gradient(115deg,rgba(17,71,155,.97),rgba(38,126,255,.92))] px-[3.2vw] py-[2.1vw] shadow-[0_28px_80px_rgba(22,91,205,.45)] backdrop-blur-xl">
          <div className="absolute -right-8 -top-20 h-64 w-64 rounded-full bg-white/10 blur-2xl"/><p className="text-[.9vw] font-bold uppercase tracking-[.32em] text-blue-100">Você chegou. A casa é sua.</p><h2 className="mt-[.45vw] text-[3.05vw] font-black uppercase leading-[1.04] tracking-[-.03em]">{welcome.message}</h2>
        </div>}
        <aside className={`birthday-enter absolute right-[3vw] top-[3vw] z-30 flex w-[18vw] min-w-[250px] max-w-[360px] flex-col overflow-hidden rounded-[1.15vw] border border-amber-200/25 bg-[radial-gradient(circle_at_top,#302814_0%,rgba(17,18,14,.96)_55%,rgba(10,12,13,.97)_100%)] p-[1.25vw] shadow-[0_24px_70px_rgba(0,0,0,.48)] backdrop-blur-xl ${data.birthdays.length <= 1 ? "aspect-square" : ""}`}>
          <div className="flex items-center gap-[.6vw]"><span className="h-[.5vw] w-[.5vw] rounded-full bg-[#f1c85b] shadow-[0_0_16px_#f1c85b]"/><p className="text-[.72vw] font-extrabold uppercase tracking-[.2em] text-[#f1c85b]">Aniversariantes do dia</p></div>
          <div className="my-[.9vw] h-px bg-gradient-to-r from-[#f1c85b]/55 to-transparent"/>
          {data.birthdays.length ? <div className={`flex flex-col gap-[.65vw] ${data.birthdays.length === 1 ? "flex-1 justify-center" : ""}`}>
            {data.birthdays.map((birthday) => <article key={birthday.id} className="flex items-center gap-[.8vw] rounded-[.8vw] border border-white/8 bg-white/[.045] p-[.7vw]">
              <div className="grid h-[3.6vw] w-[3.6vw] min-h-12 min-w-12 shrink-0 place-items-center overflow-hidden rounded-full border-2 border-[#f1c85b]/65 bg-[#27281f] shadow-[0_0_25px_rgba(241,200,91,.12)]">{birthday.photoUrl ? <img src={birthday.photoUrl} alt="" className="h-full w-full object-cover"/> : <span className="text-[1.4vw] font-black text-[#f1c85b]">{birthday.name.charAt(0)}</span>}</div>
              <div className="min-w-0"><p className="truncate text-[1.05vw] font-black leading-tight text-white">{displayBirthdayName(birthday)}</p><p className="mt-[.28vw] line-clamp-2 text-[.68vw] leading-snug text-white/55">{birthday.message || `Parabéns, ${birthday.name.split(" ")[0]}!`}</p></div>
            </article>)}
          </div> : <div className="flex flex-1 flex-col items-center justify-center px-[.6vw] text-center"><div className="grid h-[4.5vw] w-[4.5vw] place-items-center rounded-full border border-[#f1c85b]/25 bg-[#f1c85b]/5 text-[1.8vw]">✦</div><p className="mt-[1vw] text-[1.05vw] font-bold leading-snug">Hoje não temos aniversariantes.</p><p className="mt-[.45vw] text-[.7vw] leading-relaxed text-white/50">Um excelente treino para todos!</p></div>}
        </aside>
      </section>

      <footer className="flex items-center justify-between px-[.4vw]">
        <img src={data.settings.logoUrl} alt="CT Ítalo Vieira" className="h-[3.3vw] w-auto opacity-85"/>
        <div className="flex items-center gap-[1.3vw] text-right"><span className={`h-2 w-2 rounded-full ${online ? "bg-emerald-400" : "status-pulse bg-amber-400"}`}/>{data.paused && <span className="text-[.75vw] font-bold uppercase tracking-[.18em] text-amber-300">Mídia pausada</span>}{data.settings.showClock && <><p className="text-[.82vw] capitalize text-white/45">{dateText}</p><p className="text-[1.35vw] font-bold tabular-nums">{timeText}</p></>}</div>
      </footer>
    </div>
  </main>;
}

function mergeQueue(current: QueueItem[], incoming: QueueItem[]) {
  const map = new Map(current.map((item) => [item.id, item]));
  incoming.forEach((item) => map.set(item.id, item));
  return [...map.values()].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

function displayBirthdayName(birthday: Birthday) {
  const parts = birthday.name.trim().split(/\s+/);
  return birthday.showLastName ? parts.slice(0, 2).join(" ") : parts[0];
}
