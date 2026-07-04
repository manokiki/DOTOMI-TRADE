import { useState } from "react";
import { PageHeader, Card, EmptyState, Stat } from "../components/Layout";
import { ScoreDial } from "../components/ScoreDial";
import { StatusBadge } from "../components/StatusBadge";
import { ReasonList } from "../components/ReasonList";
import { SetupRow } from "../components/SetupRow";
import { usePolling } from "../lib/usePolling";
import { api } from "../lib/api";
import { formatPrice } from "../lib/format";
import { IconChart } from "../icons";

export function RecommendationPage() {
  const [selected, setSelected] = useState(null);
  const { data, error } = usePolling(() => api.topRecommendation(), { intervalMs: 8000 });

  const top = data?.top;
  const alternatives = data?.alternatives || [];
  const displayed = selected || top;

  if (error) {
    return (
      <div>
        <PageHeader title="Trade Recommendation" />
        <EmptyState
          icon={IconChart}
          title="Aucune recommandation disponible"
          description="Lancez un scan depuis la page Scanner, ou attendez le prochain cycle du scheduler en continu."
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Trade Recommendation" subtitle="Le meilleur trade actuel, avec sa justification complète" />

      <div className="grid grid-cols-12 gap-5">
        <Card className="col-span-8">
          {displayed ? (
            <>
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <div className="font-display text-2xl font-medium text-ink">{displayed.symbol}</div>
                  <div className="text-sm text-ink-soft">{displayed.direction}</div>
                </div>
                <StatusBadge status={displayed.status} />
              </div>

              <div className="flex items-center gap-8">
                <ScoreDial score={displayed.score} status={displayed.status} />
                <div className="grid flex-1 grid-cols-2 gap-x-6 gap-y-4">
                  <Stat label="Entrée" value={formatPrice(displayed.entry_price)} />
                  <Stat label="Stop-loss" value={formatPrice(displayed.stop_loss)} valueClassName="text-signal-rejected" />
                  <Stat label="TP1" value={formatPrice(displayed.tp1)} valueClassName="text-signal-authorized" />
                  <Stat label="TP2" value={formatPrice(displayed.tp2)} valueClassName="text-signal-authorized" />
                </div>
              </div>

              <div className="mt-6 border-t border-paper-line pt-5">
                <div className="mb-3 text-xs uppercase tracking-[0.1em] text-ink-faint">Pourquoi</div>
                <ReasonList reasons={displayed.reason?.split ? displayed.reason.split("; ") : displayed.reason} />
              </div>
            </>
          ) : (
            <p className="text-sm text-ink-faint">Aucune donnée à afficher.</p>
          )}
        </Card>

        <Card className="col-span-4 !p-0">
          <div className="border-b border-paper-line px-5 py-4 text-xs uppercase tracking-[0.1em] text-ink-faint">
            Alternatives
          </div>
          {alternatives.length === 0 ? (
            <p className="px-5 py-6 text-sm text-ink-faint">Aucune alternative pour le moment.</p>
          ) : (
            <div>
              {top && (
                <SetupRow setup={{ ...top, score: top.score }} rank={1} onClick={() => setSelected(top)} />
              )}
              {alternatives.map((alt, i) => (
                <SetupRow key={i} setup={alt} rank={i + 2} onClick={() => setSelected(alt)} />
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
