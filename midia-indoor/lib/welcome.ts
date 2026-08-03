export function sanitizeDisplayName(name: string) {
  return name.replace(/[<>]/g, "").replace(/\s+/g, " ").trim().slice(0, 80);
}

export function chooseWelcomeMessage(name: string, defaultMessage: string, alternatives: string[], random: boolean) {
  const pool = random && alternatives.length ? [defaultMessage, ...alternatives] : [defaultMessage];
  const template = pool[Math.floor(Math.random() * pool.length)] || defaultMessage;
  return template.replaceAll("{nome}", sanitizeDisplayName(name) || "aluno");
}

export function displayDuration(queueSize: number, normalSec: number, threshold: number, reducedSec: number) {
  return queueSize >= threshold ? reducedSec : normalSec;
}
