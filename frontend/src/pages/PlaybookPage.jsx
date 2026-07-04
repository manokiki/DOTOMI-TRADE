import { PageHeader, Card, EmptyState } from "../components/Layout";
import { IconPlaybook } from "../icons";
import { usePolling } from "../lib/usePolling";
import { api } from "../lib/api";
import { formatPct } from "../lib/format";

/**
 * Le Playbook agrège les trades gagnants par caractéristiques communes
 * (ici : le sens du trade, comme proxy simple en V1) pour faire émerger
 * les patterns qui fonctionnent réellement. Comme pour Analytics, aucune
 * statistique n'est affichée tant qu'il n'y a pas assez de trades réels.
 */
function buildPlaybookEntries(trades) {
  const closed = trades.filter((t) => t.result === "WIN" || t.result === "LOSS");
  const byDirection = {};
  for (const t of closed) {
    const key = t.direction || "INCONNU";
    byDirection[key] = byDirection[key] || { wins: 0, total: 0 };
    byDirection[key].total += 1;
    if (t.result === "WIN") byDirection[key].wins += 1;
  }
  return Object.entries(byDirection).map(([direction, { wins, total }]) => ({
    direction,
    winRate: (wins / total) * 100,
    total,
  }));
}

export function PlaybookPage() {
  const { data: trades } = usePolling(() => api.journal(), { intervalMs: 15000 });
  const entries = trades ? buildPlaybookEntries(trades) : [];

  return (
    <div>
      <PageHeader title="Playbook" subtitle="Les setups qui fonctionnent réellement, mesurés sur vos trades passés" />

      {entries.length === 0 ? (
        <EmptyState
          icon={IconPlaybook}
          title="Le Playbook se construit à partir de vos trades clôturés"
          description="Aucun pattern gagnant ne peut être identifié sans historique réel — rien n'est ici estimé à l'avance."
        />
      ) : (
        <div className="grid grid-cols-2 gap-5">
          {entries.map((entry) => (
            <Card key={entry.direction}>
              <div className="mb-3 font-display text-lg text-ink">{entry.direction}</div>
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-3xl tabular text-ink">{formatPct(entry.winRate)}</span>
                <span className="text-xs text-ink-soft">sur {entry.total} trades</span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
