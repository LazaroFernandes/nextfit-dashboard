import { EventEmitter } from "node:events";

export type TvEvent = { type: "welcome" | "playlist.reload" | "screen.reload" | "queue.clear" | "media.pause" | "media.resume" | "birthday.test"; payload?: unknown };

const globalBus = globalThis as unknown as { tvEventBus?: EventEmitter };
export const tvEventBus = globalBus.tvEventBus ?? new EventEmitter();
tvEventBus.setMaxListeners(200);
if (!globalBus.tvEventBus) globalBus.tvEventBus = tvEventBus;

export function emitTvEvent(event: TvEvent) {
  tvEventBus.emit("tv", event);
}
