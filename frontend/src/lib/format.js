/**
 * Utilitaires partagés : formatage des nombres/prix, et correspondance
 * statut -> couleur de signal (jamais codée en dur dans les composants,
 * pour rester cohérente partout dans l'interface).
 */

export function formatPrice(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

export function formatScore(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(1);
}

export function formatPct(value, digits = 2) {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toFixed(digits)}%`;
}

export const STATUS_LABELS = {
  AUTHORIZED: "Autorisé",
  WATCH: "Surveiller",
  WEAK: "Faible",
  REJECTED: "Rejeté",
};

export const STATUS_COLOR_CLASS = {
  AUTHORIZED: "text-signal-authorized",
  WATCH: "text-signal-watch",
  WEAK: "text-signal-weak",
  REJECTED: "text-signal-rejected",
};

export const STATUS_BG_CLASS = {
  AUTHORIZED: "bg-signal-authorized/10 border-signal-authorized/30",
  WATCH: "bg-signal-watch/10 border-signal-watch/30",
  WEAK: "bg-signal-weak/10 border-signal-weak/30",
  REJECTED: "bg-signal-rejected/10 border-signal-rejected/30",
};

export function statusLabel(status) {
  return STATUS_LABELS[status] || status || "—";
}
