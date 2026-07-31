export function firstName(name: string) {
  return name.trim().split(/\s+/)[0] || "aluno";
}

export function sanitizeDisplayName(name: string) {
  return name.replace(/[<>]/g, "").replace(/\s+/g, " ").trim().slice(0, 80);
}

export function chooseWelcomeMessage(name: string, defaultMessage: string, alternatives: string[], random: boolean) {
  const pool = random && alternatives.length ? [defaultMessage, ...alternatives] : [defaultMessage];
  const template = pool[Math.floor(Math.random() * pool.length)] || defaultMessage;
  return template.replaceAll("{nome}", firstName(sanitizeDisplayName(name)));
}

export function displayDuration(queueSize: number, normalSec: number, threshold: number, reducedSec: number) {
  return queueSize >= threshold ? reducedSec : normalSec;
}
