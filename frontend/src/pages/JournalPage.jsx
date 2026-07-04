import { PageHeader, Card, EmptyState } from "../components/Layout";
import { IconJournal, IconArrowUp, IconArrowDown } from "../icons";
import { usePolling } from "../lib/usePolling";
import { api } from "../lib/api";
import { formatPrice } from "../lib/format";

function ResultTag({ result }) {
  const map = {
    WIN: "text-signal-authorized",
    LOSS: "text-signal-rejected",
    BREAKEVEN: "text-ink-soft",
    OPEN: "text-signal-watch",
  };
  return <span className={`font-medium ${map[result] || "text-ink-soft"}`}>{result}</span>;
}

export function JournalPage() {
  const { data: trades } = usePolling(() => api.journal(), { intervalMs: 10000 });

  return (
    <div>
      <PageHeader title="Journal" subtitle="Historique complet des trades, journalisés tels qu'exécutés" />

      <Card className="!p-0">
        {!trades || trades.length === 0 ? (
          <div className="p-2">
            <EmptyState
              icon={IconJournal}
              title="Aucun trade journalisé"
              description="Chaque trade ouvert via l'API apparaîtra ici avec son résultat réel — jamais une estimation."
            />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-paper-line text-left text-[11px] uppercase tracking-[0.08em] text-ink-faint">
                <th className="px-5 py-3 font-normal">Actif</th>
                <th className="px-5 py-3 font-normal">Sens</th>
                <th className="px-5 py-3 font-normal">Entrée</th>
                <th className="px-5 py-3 font-normal">Sortie</th>
                <th className="px-5 py-3 font-normal">PnL</th>
                <th className="px-5 py-3 font-normal">R</th>
                <th className="px-5 py-3 font-normal">Résultat</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => {
                const Icon = t.direction === "BUY" ? IconArrowUp : IconArrowDown;
                return (
                  <tr key={t.id} className="border-b border-paper-line last:border-b-0 hover:bg-paper/50">
                    <td className="px-5 py-3 font-display font-medium text-ink">{t.symbol}</td>
                    <td className="px-5 py-3">
                      <Icon size={14} className={t.direction === "BUY" ? "text-signal-authorized" : "text-signal-rejected"} />
                    </td>
                    <td className="px-5 py-3 font-mono tabular text-ink-soft">{formatPrice(t.entry_price)}</td>
                    <td className="px-5 py-3 font-mono tabular text-ink-soft">{formatPrice(t.exit_price)}</td>
                    <td className={`px-5 py-3 font-mono tabular ${t.pnl > 0 ? "text-signal-authorized" : t.pnl < 0 ? "text-signal-rejected" : "text-ink-soft"}`}>
                      {t.pnl !== null && t.pnl !== undefined ? formatPrice(t.pnl) : "—"}
                    </td>
                    <td className="px-5 py-3 font-mono tabular text-ink-soft">
                      {t.r_multiple !== null && t.r_multiple !== undefined ? t.r_multiple.toFixed(2) : "—"}
                    </td>
                    <td className="px-5 py-3">
                      <ResultTag result={t.result} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
