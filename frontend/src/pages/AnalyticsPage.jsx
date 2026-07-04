import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { PageHeader, Card, Stat, EmptyState } from "../components/Layout";
import { IconLayers } from "../icons";
import { usePolling } from "../lib/usePolling";
import { api } from "../lib/api";
import { formatPct } from "../lib/format";

function buildEquityCurve(trades) {
  const closed = trades.filter((t) => t.r_multiple !== null && t.r_multiple !== undefined).reverse();
  let cumulative = 0;
  return closed.map((t, i) => {
    cumulative += t.r_multiple;
    return { index: i + 1, cumulative: Number(cumulative.toFixed(2)) };
  });
}

export function AnalyticsPage() {
  const { data: analytics } = usePolling(() => api.analytics(), { intervalMs: 15000 });
  const { data: trades } = usePolling(() => api.journal(), { intervalMs: 15000 });

  const noData = !analytics || analytics.trades_count === 0;
  const equityCurve = trades ? buildEquityCurve(trades) : [];

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="Calculé exclusivement à partir de trades réellement journalisés — jamais une projection"
      />

      {noData ? (
        <EmptyState
          icon={IconLayers}
          title="Pas encore de statistique calculable"
          description={analytics?.message || "Journalisez des trades via l'API pour voir apparaître vos performances réelles ici."}
        />
      ) : (
        <div className="grid grid-cols-12 gap-5">
          <Card className="col-span-3">
            <Stat label="Trades clôturés" value={analytics.trades_count} />
          </Card>
          <Card className="col-span-3">
            <Stat label="Taux de réussite" value={formatPct(analytics.win_rate_pct)} />
          </Card>
          <Card className="col-span-3">
            <Stat label="Profit factor" value={analytics.profit_factor ?? "—"} />
          </Card>
          <Card className="col-span-3">
            <Stat label="R moyen / trade" value={analytics.average_r_multiple ?? "—"} />
          </Card>

          <Card className="col-span-12">
            <div className="mb-4 text-xs uppercase tracking-[0.1em] text-ink-faint">
              Courbe d'équité cumulée (en unités R)
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={equityCurve}>
                <CartesianGrid stroke="#E4E0D6" vertical={false} />
                <XAxis
                  dataKey="index"
                  stroke="#A6A399"
                  tick={{ fontSize: 11, fontFamily: "IBM Plex Mono" }}
                  axisLine={{ stroke: "#E4E0D6" }}
                  tickLine={false}
                />
                <YAxis
                  stroke="#A6A399"
                  tick={{ fontSize: 11, fontFamily: "IBM Plex Mono" }}
                  axisLine={{ stroke: "#E4E0D6" }}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#FFFFFF",
                    border: "1px solid #E4E0D6",
                    borderRadius: 2,
                    fontSize: 12,
                    fontFamily: "IBM Plex Mono",
                  }}
                />
                <Line type="monotone" dataKey="cumulative" stroke="#173404" strokeWidth={1.75} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}
    </div>
  );
}
