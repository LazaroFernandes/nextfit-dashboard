const globalRate = globalThis as unknown as { entryRate?: Map<string, number[]> };
const attempts = globalRate.entryRate ?? new Map<string, number[]>();
globalRate.entryRate = attempts;

export function allowRequest(key: string, limit = 60, windowMs = 60_000) {
  const now = Date.now();
  const recent = (attempts.get(key) || []).filter((value) => now - value < windowMs);
  if (recent.length >= limit) return false;
  recent.push(now);
  attempts.set(key, recent);
  return true;
}
