import { useNavigate } from "react-router-dom";
import { PageHeader, Card, Stat, ErrorBanner } from "../components/Layout";
import { ScoreDial } from "../components/ScoreDial";
import { StatusBadge } from "../components/StatusBadge";
import { ReasonList } from "../components/ReasonList";
import { usePolling } from "../lib/usePolling";
import { api } from "../lib/api";
import { formatPrice, formatPct } from "../lib/format";
import { IconPulse, IconShield, IconScan } from "../icons";

export function DashboardPage() {
  const navigate = useNavigate();
  const { data: top, error: topError } = usePolling(() => api.topRecommendation().catch(() => null), {
    intervalMs: 8000,
  });
  const { data: health } = usePolling(() => api.health(), { intervalMs: 10000 });
  const { data: analytics } = usePolling(() => api.analytics(), { intervalMs: 15000 });

  const topSetup = top?.top;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Vue d'ensemble du système en temps réel"
        action={
          <div className="flex items-center gap-2 text-xs text-ink-soft">
            <span
              className={`h-1.5 w-1.5 rounded-full ${health?.status === "ok" ? "bg-signal-authorized" : "bg-signal-rejected"}`}
            />
            {health?.status === "ok" ? "Données de marché accessibles" : "Source de données dégradée"}
          </div>
        }
      />

      <div className="grid grid-cols-12 gap-5">
        <Card className="col-span-7">
          <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-[0.1em] text-ink-faint">
            <IconScan size={14} />
            Meilleure opportunité actuelle
          </div>

          {!top && !topError && <p className="text-sm text-ink-faint">Recherche en cours...</p>}
          {topError && (
            <ErrorBanner message="Aucun setup enregistré pour le moment. Lancez un scan depuis la page Scanner." />
          )}

          {topSetup && (
            <div className="flex items-center gap-8">
              <ScoreDial score={topSetup.score} status={topSetup.status} />
              <div className="flex-1">
                <div className="mb-2 flex items-center gap-3">
                  <span className="font-display text-xl font-medium text-ink">{topSetup.symbol}</span>
                  <StatusBadge status={topSetup.status} />
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <Stat label="Entrée" value={formatPrice(topSetup.entry_price)} />
                  <Stat label="Stop" value={formatPrice(topSetup.stop_loss)} valueClassName="text-signal-rejected" />
                  <Stat label="TP1" value={formatPrice(topSetup.tp1)} valueClassName="text-signal-authorized" />
                </div>
                <button
                  onClick={() => navigate("/recommendation")}
                  className="mt-4 text-xs font-medium uppercase tracking-[0.08em] text-signal-authorized hover:underline"
                >
                  Voir l'analyse complète →
                </button>
              </div>
            </div>
          )}
        </Card>

        <Card className="col-span-5">
          <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-[0.1em] text-ink-faint">
            <IconShield size={14} />
            État du risque
          </div>
          {!analytics || analytics.trades_count === 0 ? (
            <p className="text-sm text-ink-faint">
              Aucun trade journalisé pour le moment — aucune statistique de risque calculable.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <Stat label="Trades journalisés" value={analytics.trades_count} />
              <Stat label="Taux de réussite" value={formatPct(analytics.win_rate_pct)} />
              <Stat label="Profit factor" value={analytics.profit_factor ?? "—"} />
              <Stat label="R moyen" value={analytics.average_r_multiple ?? "—"} />
            </div>
          )}
        </Card>

        <Card className="col-span-12">
          <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-[0.1em] text-ink-faint">
            <IconPulse size={14} />
            Pourquoi ce score
          </div>
          {topSetup ? (
            <ReasonList reasons={topSetup.reason} />
          ) : (
            <p className="text-sm text-ink-faint">Pas de setup à expliquer pour le moment.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
