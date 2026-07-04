/**
 * SystemSignalsPage — Historique complet de tous les signaux système.
 * Compatible avec l'architecture existante.
 */
import { useState } from "react";
import { PageHeader, Card, EmptyState } from "../components/Layout";
import { StatusBadge } from "../components/StatusBadge";
import { usePolling } from "../lib/usePolling";
import { api } from "../lib/api";
import { formatPrice } from "../lib/format";

// ── Icônes ────────────────────────────────────────────────────────────────────
function IconList({ size = 28, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none"
      stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" className={className}>
      <path d="M4 7h20M4 14h14M4 21h17" />
    </svg>
  );
}
function ArrowUp({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 10V2M6 2L2 6M6 2l4 4" />
    </svg>
  );
}
function ArrowDown({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" fill="none"
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 2v8M6 10L2 6M6 10l4-4" />
    </svg>
  );
}

// ── Composants ────────────────────────────────────────────────────────────────
function ScoreBar({ score }) {
  const color = score >= 85 ? "bg-signal-authorized"
              : score >= 70 ? "bg-signal-watch"
              : "bg-signal-rejected";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-paper-line">
        <div className={`h-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="w-7 text-right font-mono text-xs tabular text-ink">{score.toFixed(0)}</span>
    </div>
  );
}

function MacroBadge({ ctx }) {
  const colors = { FAVORABLE: "text-signal-authorized", NEUTRAL: "text-ink-soft",
                   HOSTILE: "text-signal-watch", CRISIS: "text-signal-rejected" };
  return <span className={`font-mono text-[10px] font-medium ${colors[ctx] || "text-ink-faint"}`}>{ctx || "—"}</span>;
}

// ── Ligne expandable ──────────────────────────────────────────────────────────
function SignalRow({ signal }) {
  const [open, setOpen] = useState(false);
  const isLong = signal.direction === "BUY";
  const date = signal.signaled_at
    ? new Date(signal.signaled_at).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
    : "—";

  const subScores = [
    ["Régime",       signal.score_regime   ?? 0, 15],
    ["Structure",    signal.score_structure ?? 0, 20],
    ["Liquidité",    signal.score_liquidity ?? 0, 15],
    ["Pullback",     signal.score_pullback  ?? 0, 10],
    ["Timing",       signal.score_timing    ?? 0, 10],
    ["Confirmation", signal.score_confirm   ?? 0, 10],
    ["Risque",       signal.score_risk      ?? 0, 10],
    ["Macro",        signal.score_macro     ?? 0, 5],
    ["On-Chain",     signal.score_onchain   ?? 0, 5],
  ];

  return (
    <>
      <tr onClick={() => setOpen(v => !v)}
        className="cursor-pointer border-b border-paper-line last:border-b-0 hover:bg-paper/50">
        <td className="px-4 py-3 font-mono text-[11px] tabular text-ink-faint">{date}</td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-1.5">
            <span className={isLong ? "text-signal-authorized" : "text-signal-rejected"}>
              {isLong ? <ArrowUp /> : <ArrowDown />}
            </span>
            <span className="font-medium text-ink">{signal.symbol?.replace("USDT", "")}</span>
            <span className="text-[10px] text-ink-faint">/USDT</span>
          </div>
        </td>
        <td className="px-4 py-3"><ScoreBar score={signal.total_score} /></td>
        <td className="px-4 py-3"><StatusBadge status={signal.status} size="sm" /></td>
        <td className="px-4 py-3 font-mono text-[11px] text-ink-soft">{signal.session_name || "—"}</td>
        <td className="px-4 py-3 font-mono text-[11px] tabular text-ink-soft">
          {signal.entry_price ? formatPrice(signal.entry_price) : "—"}
        </td>
        <td className="px-4 py-3 font-mono text-[11px] tabular text-ink-soft">
          {signal.rrr ? `${signal.rrr.toFixed(2)}R` : "—"}
        </td>
        <td className="px-4 py-3"><MacroBadge ctx={signal.macro_context} /></td>
        <td className="px-4 py-3 font-mono text-[11px]">
          {signal.was_executed
            ? <span className="text-signal-authorized">#{signal.trade_id}</span>
            : <span className="text-ink-faint">—</span>}
        </td>
      </tr>

      {open && (
        <tr className="border-b border-paper-line bg-paper/40">
          <td colSpan={9} className="px-4 py-4">
            <div className="grid grid-cols-3 gap-6">
              {/* Sous-scores */}
              <div>
                <div className="mb-2 text-[10px] uppercase tracking-[0.1em] text-ink-faint">Scores détaillés</div>
                <div className="space-y-1.5">
                  {subScores.map(([label, val, weight]) => (
                    <div key={label} className="flex items-center gap-2">
                      <span className="w-24 text-[11px] text-ink-soft">{label}</span>
                      <div className="h-1 flex-1 overflow-hidden rounded-full bg-paper-line">
                        <div className="h-full bg-ink/25" style={{ width: `${val}%` }} />
                      </div>
                      <span className="w-16 text-right font-mono text-[10px] tabular text-ink-faint">
                        {val.toFixed(0)} / {weight * 10}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Niveaux + contexte */}
              <div>
                <div className="mb-2 text-[10px] uppercase tracking-[0.1em] text-ink-faint">Niveaux</div>
                <div className="space-y-1.5 font-mono text-[11px]">
                  {[
                    ["Entry",   signal.entry_price ? formatPrice(signal.entry_price) : "—", "text-ink"],
                    ["Stop",    signal.stop_loss   ? formatPrice(signal.stop_loss)   : "—", "text-signal-rejected"],
                    ["TP1",     signal.tp1         ? formatPrice(signal.tp1)         : "—", "text-signal-authorized"],
                    ["TP2",     signal.tp2         ? formatPrice(signal.tp2)         : "—", "text-signal-authorized"],
                    ["R:R",     signal.rrr         ? `${signal.rrr.toFixed(2)} : 1` : "—", "text-ink-soft"],
                    ["Fenêtre", signal.entry_window || "—", "text-ink-soft"],
                  ].map(([l, v, cls]) => (
                    <div key={l} className="flex justify-between gap-3">
                      <span className="text-ink-faint">{l}</span>
                      <span className={`tabular ${cls}`}>{v}</span>
                    </div>
                  ))}
                </div>
                <div className="mb-2 mt-4 text-[10px] uppercase tracking-[0.1em] text-ink-faint">Contexte</div>
                <div className="space-y-1.5 font-mono text-[11px]">
                  {[
                    ["Macro",   signal.macro_context || "—"],
                    ["F&G",     signal.fear_greed != null ? `${signal.fear_greed}/100` : "—"],
                    ["VIX",     signal.vix != null ? signal.vix.toFixed(1) : "—"],
                    ["Funding", signal.funding_rate != null ? `${signal.funding_rate.toFixed(4)}%` : "—"],
                  ].map(([l, v]) => (
                    <div key={l} className="flex justify-between gap-3">
                      <span className="text-ink-faint">{l}</span>
                      <span className="text-ink-soft">{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Raisons */}
              <div>
                <div className="mb-2 text-[10px] uppercase tracking-[0.1em] text-ink-faint">Raisons du signal</div>
                <ul className="space-y-1">
                  {(signal.reasons || []).map((r, i) => (
                    <li key={i} className="text-[11px] leading-snug text-ink-soft">— {r}</li>
                  ))}
                  {(!signal.reasons || signal.reasons.length === 0) && (
                    <li className="text-[11px] text-ink-faint">Aucune raison enregistrée.</li>
                  )}
                </ul>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Filtres ───────────────────────────────────────────────────────────────────
function Pill({ active, onClick, children }) {
  return (
    <button onClick={onClick}
      className={`rounded-sm px-2.5 py-1 text-[11px] font-medium transition-colors ${
        active ? "bg-ink text-paper" : "bg-paper text-ink-soft hover:bg-paper-line"
      }`}>
      {children}
    </button>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export function SystemSignalsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [symbolFilter, setSymbolFilter] = useState("");

  const { data: signals, isLoading } = usePolling(
    () => api.systemSignals({ status: statusFilter || undefined, symbol: symbolFilter || undefined }),
    { intervalMs: 15000 }
  );

  const total      = signals?.length ?? 0;
  const authorized = signals?.filter(s => s.status === "AUTHORIZED").length ?? 0;
  const executed   = signals?.filter(s => s.was_executed).length ?? 0;
  const execRate   = authorized > 0 ? `${((executed / authorized) * 100).toFixed(0)}%` : "—";

  return (
    <div>
      <PageHeader
        title="Historique Système"
        subtitle="Tous les signaux générés par le moteur — exécutés ou non. La mémoire complète."
      />

      {/* Stats */}
      <div className="mb-5 grid grid-cols-4 gap-4">
        {[
          { label: "Signaux total",  value: total },
          { label: "Autorisés",      value: authorized },
          { label: "Exécutés",       value: executed },
          { label: "Taux exécution", value: execRate },
        ].map(({ label, value }) => (
          <Card key={label}>
            <div className="text-[10px] uppercase tracking-[0.1em] text-ink-faint">{label}</div>
            <div className="mt-1 font-mono text-xl tabular text-ink">{value}</div>
          </Card>
        ))}
      </div>

      {/* Filtres */}
      <Card className="mb-5">
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-ink-faint">Statut</span>
            <div className="flex gap-1">
              {[["Tous",""],["Autorisés","AUTHORIZED"],["Surveiller","WATCH"],["Rejetés","REJECTED"]].map(([l,v]) => (
                <Pill key={v} active={statusFilter === v} onClick={() => setStatusFilter(v)}>{l}</Pill>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-ink-faint">Actif</span>
            <div className="flex gap-1">
              {[["Tous",""],["BTC","BTCUSDT"],["ETH","ETHUSDT"],["SOL","SOLUSDT"]].map(([l,v]) => (
                <Pill key={v} active={symbolFilter === v} onClick={() => setSymbolFilter(v)}>{l}</Pill>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card className="!p-0">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-ink-faint">Chargement...</div>
        ) : !signals || signals.length === 0 ? (
          <div className="p-4">
            <EmptyState icon={IconList} title="Aucun signal archivé"
              description="Chaque signal généré apparaîtra ici — exécuté ou non." />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-line">
                  {["Date / Heure","Actif","Score","Statut","Session","Entrée","R:R","Macro","Exécuté"].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-normal text-[10px] uppercase tracking-[0.08em] text-ink-faint">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {signals.map(s => <SignalRow key={s.id} signal={s} />)}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <p className="mt-3 text-[11px] text-ink-faint">
        Cliquer sur une ligne pour voir le détail complet : scores, niveaux, contexte macro, raisons.
      </p>
    </div>
  );
}
