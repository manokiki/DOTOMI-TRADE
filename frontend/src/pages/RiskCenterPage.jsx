import { useMemo, useState } from "react";
import { PageHeader, Card, Stat } from "../components/Layout";
import { IconRiskCenter } from "../icons";
import { formatPrice } from "../lib/format";

/**
 * Calculateur de sizing côté interface — reproduit la formule du Risk
 * Center backend (risque fixe % du capital / distance au stop) pour une
 * simulation instantanée sans aller-retour serveur. Le calcul réellement
 * appliqué au moment d'autoriser un trade reste celui du backend
 * (app/risk/risk_center.py) ; ce panneau est un outil de préparation.
 */
function computeSizing({ capital, riskPct, entry, stop }) {
  if (!capital || !entry || !stop || entry === stop) return null;
  const riskBudget = capital * (riskPct / 100);
  const stopDistance = Math.abs(entry - stop);
  const quantity = riskBudget / stopDistance;
  return { riskBudget, quantity };
}

export function RiskCenterPage() {
  const [capital, setCapital] = useState(100);
  const [riskPct, setRiskPct] = useState(1);
  const [entry, setEntry] = useState(61250);
  const [stop, setStop] = useState(61020);

  const sizing = useMemo(
    () => computeSizing({ capital: Number(capital), riskPct: Number(riskPct), entry: Number(entry), stop: Number(stop) }),
    [capital, riskPct, entry, stop]
  );

  return (
    <div>
      <PageHeader title="Risk Center" subtitle="Règles de risque, plafonds et calculateur de taille de position" />

      <div className="grid grid-cols-12 gap-5">
        <Card className="col-span-5">
          <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-[0.1em] text-ink-faint">
            <IconRiskCenter size={14} />
            Calculateur de sizing
          </div>

          <div className="space-y-4">
            <Field label="Capital ($)" value={capital} onChange={setCapital} />
            <Field label="Risque par trade (%)" value={riskPct} onChange={setRiskPct} step="0.1" />
            <Field label="Prix d'entrée" value={entry} onChange={setEntry} />
            <Field label="Stop-loss" value={stop} onChange={setStop} />
          </div>

          {sizing && (
            <div className="mt-5 grid grid-cols-2 gap-4 border-t border-paper-line pt-4">
              <Stat label="Montant risqué" value={formatPrice(sizing.riskBudget)} suffix="$" />
              <Stat label="Quantité suggérée" value={sizing.quantity.toFixed(6)} />
            </div>
          )}
        </Card>

        <Card className="col-span-7">
          <div className="mb-4 text-xs uppercase tracking-[0.1em] text-ink-faint">Plafonds actifs</div>
          <div className="space-y-4">
            <LimitRow label="Perte journalière maximale" value="5 %" />
            <LimitRow label="Perte hebdomadaire maximale" value="10 %" />
            <LimitRow label="Trades maximum par jour" value="5" />
            <LimitRow label="Ratio risque/rendement minimum" value="1.5" />
            <LimitRow label="Plafond de sécurité absolu (risque/trade)" value="10 %" highlight />
          </div>
          <p className="mt-5 border-t border-paper-line pt-4 text-xs leading-relaxed text-ink-faint">
            Ces valeurs reflètent la configuration par défaut du backend
            (app/config.py). Le plafond de sécurité absolu n'est jamais
            contournable par simple paramétrage utilisateur.
          </p>
        </Card>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, step = "1" }) {
  return (
    <div>
      <label className="mb-1.5 block text-[11px] uppercase tracking-[0.1em] text-ink-faint">{label}</label>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-sm border border-paper-line bg-paper px-3 py-2 font-mono text-sm tabular text-ink focus:border-signal-authorized focus:outline-none"
      />
    </div>
  );
}

function LimitRow({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between border-b border-paper-line pb-3 last:border-b-0">
      <span className="text-sm text-ink-soft">{label}</span>
      <span className={`font-mono text-sm tabular ${highlight ? "text-signal-rejected" : "text-ink"}`}>
        {value}
      </span>
    </div>
  );
}
