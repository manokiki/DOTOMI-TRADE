import { IconCheck, IconBlocked } from "../icons";

/**
 * Affiche les raisons d'un score : les facteurs positifs en vert, les
 * blocages (préfixés "Bloqué:" par le backend) en rouge brique. Les motifs
 * de blocage doivent toujours rester visibles et distincts des raisons
 * positives — c'est ce qui rend le système traçable (section 0 du prompt
 * maître backend : chaque blocage doit être explicable).
 */
export function ReasonList({ reasons = [] }) {
  if (!reasons.length) {
    return <p className="text-sm text-ink-faint">Aucun facteur particulier détecté.</p>;
  }

  return (
    <ul className="space-y-1.5">
      {reasons.map((reason, i) => {
        const isBlock = reason.startsWith("Bloqué:");
        const Icon = isBlock ? IconBlocked : IconCheck;
        const text = isBlock ? reason.replace("Bloqué:", "").trim() : reason;
        return (
          <li
            key={i}
            className={`flex items-start gap-2 text-sm ${isBlock ? "text-signal-rejected" : "text-ink"}`}
          >
            <Icon size={14} className="mt-0.5 shrink-0" />
            <span>{text}</span>
          </li>
        );
      })}
    </ul>
  );
}
