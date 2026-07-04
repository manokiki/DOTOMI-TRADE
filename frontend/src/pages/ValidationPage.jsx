import { useState } from "react";
import { PageHeader, Card, ErrorBanner } from "../components/Layout";
import { StatusBadge } from "../components/StatusBadge";
import { IconCheck, IconBlocked, IconShield } from "../icons";
import { api } from "../lib/api";

const RULES = [
  "Biais directionnel clair (trend_bias)",
  "Score de pullback suffisant",
  "Score de timing suffisant",
  "Score de risque suffisant",
  "Score total ≥ seuil d'autorisation",
  "Ratio risque/rendement suffisant",
  "Perte journalière sous le plafond",
  "Perte hebdomadaire sous le plafond",
  "Nombre de trades journaliers non atteint",
];

export function ValidationPage() {
  const [setupId, setSetupId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function check() {
    setError(null);
    setResult(null);
    try {
      const data = await api.validateSetup(setupId);
      setResult(data);
    } catch (err) {
      setError(err.message);
    }
  }

  const blockedReasons = (result?.reason || "")
    .split(";")
    .map((r) => r.trim())
    .filter((r) => r.startsWith("Bloqué"));

  return (
    <div>
      <PageHeader title="Validation Engine" subtitle="Vérifie un setup contre l'ensemble des règles obligatoires" />

      <Card className="mb-5">
        <div className="flex items-end gap-3">
          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-[0.1em] text-ink-faint">
              ID du setup
            </label>
            <input
              value={setupId}
              onChange={(e) => setSetupId(e.target.value)}
              placeholder="ex: 1"
              className="w-32 rounded-sm border border-paper-line bg-paper px-3 py-2 font-mono text-sm text-ink focus:border-signal-authorized focus:outline-none"
            />
          </div>
          <button
            onClick={check}
            className="flex items-center gap-2 rounded-sm bg-ink px-4 py-2 text-sm font-medium text-paper hover:opacity-90"
          >
            <IconShield size={15} />
            Vérifier
          </button>
        </div>
      </Card>

      {error && <ErrorBanner message={error} />}

      {result && (
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <div className="font-display text-lg text-ink">
              {result.symbol} · {result.direction}
            </div>
            <StatusBadge status={result.status} />
          </div>

          <div className="space-y-2.5">
            {RULES.map((rule) => {
              const failed = blockedReasons.some((b) => b.toLowerCase().includes(rule.split(" ")[0].toLowerCase()));
              return (
                <div key={rule} className="flex items-center gap-2.5 text-sm">
                  {failed ? (
                    <IconBlocked size={15} className="shrink-0 text-signal-rejected" />
                  ) : (
                    <IconCheck size={15} className="shrink-0 text-signal-authorized" />
                  )}
                  <span className={failed ? "text-signal-rejected" : "text-ink"}>{rule}</span>
                </div>
              );
            })}
          </div>

          {result.reason && (
            <div className="mt-5 border-t border-paper-line pt-4 font-mono text-xs text-ink-soft">
              {result.reason}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
