import { useState } from "react";
import { PageHeader, Card, ErrorBanner, Stat } from "../components/Layout";
import { ScoreDial } from "../components/ScoreDial";
import { StatusBadge } from "../components/StatusBadge";
import { ReasonList } from "../components/ReasonList";
import { api } from "../lib/api";
import { formatPrice, formatScore } from "../lib/format";
import { IconScan } from "../icons";

const SUB_SCORE_LABELS = {
  regime: "Régime",
  structure: "Structure",
  liquidity: "Liquidité",
  pullback: "Pullback",
  timing: "Timing",
  confirmation: "Confirmation",
  risk: "Risque",
};

function SubScoreBar({ label, value }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-ink-soft">{label}</span>
        <span className="font-mono tabular text-ink">{formatScore(value)}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-paper-line">
        <div
          className="h-full rounded-full bg-signal-authorized/70"
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

export function ScannerPage() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("15m");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function runScan() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.scan(symbol, timeframe);
      setResult(data);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader title="Market Scanner" subtitle="Lance un cycle d'analyse complet sur un actif" />

      <Card className="mb-5">
        <div className="flex items-end gap-4">
          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-[0.1em] text-ink-faint">
              Symbole
            </label>
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="w-40 rounded-sm border border-paper-line bg-paper px-3 py-2 font-mono text-sm text-ink focus:border-signal-authorized focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-[0.1em] text-ink-faint">
              Intervalle
            </label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="rounded-sm border border-paper-line bg-paper px-3 py-2 font-mono text-sm text-ink focus:border-signal-authorized focus:outline-none"
            >
              {["1m", "5m", "15m", "30m", "1h", "4h", "1d"].map((tf) => (
                <option key={tf} value={tf}>
                  {tf}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={runScan}
            disabled={loading}
            className="flex items-center gap-2 rounded-sm bg-ink px-4 py-2 text-sm font-medium text-paper transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            <IconScan size={15} />
            {loading ? "Analyse en cours..." : "Lancer le scan"}
          </button>
        </div>
      </Card>

      {error && <ErrorBanner message={error} />}

      {result && (
        <div className="grid grid-cols-12 gap-5">
          <Card className="col-span-4">
            <div className="flex flex-col items-center">
              <ScoreDial score={result.score} status={result.status} />
              <StatusBadge status={result.status} />
              <div className="mt-4 w-full space-y-2 border-t border-paper-line pt-4">
                <Stat label="Entrée" value={formatPrice(result.entry_price)} />
                <Stat label="Stop-loss" value={formatPrice(result.stop_loss)} valueClassName="text-signal-rejected" />
                <Stat label="TP1" value={formatPrice(result.tp1)} valueClassName="text-signal-authorized" />
                <Stat label="TP2" value={formatPrice(result.tp2)} valueClassName="text-signal-authorized" />
                <Stat label="Ratio R/R" value={result.rrr ?? "—"} />
              </div>
            </div>
          </Card>

          <Card className="col-span-4">
            <div className="mb-4 text-xs uppercase tracking-[0.1em] text-ink-faint">
              Détail des sous-scores
            </div>
            <div className="space-y-3.5">
              {Object.entries(result.sub_scores || {}).map(([key, value]) => (
                <SubScoreBar key={key} label={SUB_SCORE_LABELS[key] || key} value={value} />
              ))}
            </div>
          </Card>

          <Card className="col-span-4">
            <div className="mb-4 text-xs uppercase tracking-[0.1em] text-ink-faint">
              Pourquoi
            </div>
            <ReasonList reasons={result.reason} />
          </Card>
        </div>
      )}
    </div>
  );
}
