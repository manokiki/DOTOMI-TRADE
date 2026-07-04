import { PageHeader, Card, EmptyState } from "../components/Layout";
import { IconAlerts, IconBlocked, IconCheck } from "../icons";
import { usePolling } from "../lib/usePolling";
import { api } from "../lib/api";

export function AlertsPage() {
  const { data: system } = usePolling(() => api.healthSystem(24).catch(() => null), { intervalMs: 10000 });
  const { data: markets } = usePolling(() => api.healthMarkets().catch(() => null), { intervalMs: 10000 });

  const components = system?.components ? Object.entries(system.components) : [];

  return (
    <div>
      <PageHeader title="Alertes" subtitle="État de santé du système, sur les dernières 24 heures" />

      <div className="grid grid-cols-12 gap-5">
        <Card className="col-span-7 !p-0">
          <div className="border-b border-paper-line px-5 py-4 text-xs uppercase tracking-[0.1em] text-ink-faint">
            Composants surveillés
          </div>
          {components.length === 0 ? (
            <div className="p-2">
              <EmptyState
                icon={IconAlerts}
                title="Aucune donnée de santé pour le moment"
                description="Apparaîtra dès que le scheduler ou un scan manuel aura tourné au moins une fois."
              />
            </div>
          ) : (
            <div>
              {components.map(([name, info]) => {
                const isHealthy = info.last_status === "OK";
                return (
                  <div
                    key={name}
                    className="flex items-center justify-between border-b border-paper-line px-5 py-3.5 last:border-b-0"
                  >
                    <div className="flex items-center gap-2.5">
                      {isHealthy ? (
                        <IconCheck size={15} className="text-signal-authorized" />
                      ) : (
                        <IconBlocked size={15} className="text-signal-rejected" />
                      )}
                      <span className="font-mono text-sm text-ink">{name}</span>
                    </div>
                    <div className="text-xs text-ink-soft">
                      {info.ok_count} OK · {info.down_count} échec(s)
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="col-span-5">
          <div className="mb-4 text-xs uppercase tracking-[0.1em] text-ink-faint">Marchés</div>
          {!markets?.scheduler_enabled ? (
            <p className="text-sm text-ink-faint">
              Scheduler non activé — santé par marché indisponible. Voir SCHEDULER_ENABLED dans la configuration.
            </p>
          ) : (
            <div className="space-y-2.5">
              {Object.entries(markets.markets || {}).map(([market, ok]) => (
                <div key={market} className="flex items-center justify-between text-sm">
                  <span className="capitalize text-ink">{market}</span>
                  <span className={ok ? "text-signal-authorized" : "text-signal-rejected"}>
                    {ok ? "Accessible" : "Inaccessible"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
