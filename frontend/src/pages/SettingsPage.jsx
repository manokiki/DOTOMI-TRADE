import { PageHeader, Card } from "../components/Layout";
import { IconSettings } from "../icons";

/**
 * En V1, les règles de trading sont configurées côté backend
 * (app/config.py / table TradingRuleSet) plutôt que modifiables depuis
 * cette page — l'édition en direct depuis l'interface est une extension
 * naturelle mais volontairement hors-scope ici pour rester cohérent avec
 * "pas d'action qui contourne les garde-fous sans review explicite".
 * Cette page affiche donc la configuration active, en lecture seule.
 */
const RULESET_DISPLAY = [
  { label: "Risque maximum par trade", value: "1 %" },
  { label: "Perte journalière maximale", value: "5 %" },
  { label: "Perte hebdomadaire maximale", value: "10 %" },
  { label: "Trades maximum par jour", value: "5" },
  { label: "Ratio risque/rendement minimum", value: "1.5" },
  { label: "Score minimum pour autorisation", value: "85 / 100" },
  { label: "Marchés autorisés", value: "Crypto (extensible forex / actions)" },
];

export function SettingsPage() {
  return (
    <div>
      <PageHeader title="Profil & règles" subtitle="Configuration active du moteur de décision" />

      <div className="grid grid-cols-12 gap-5">
        <Card className="col-span-7">
          <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-[0.1em] text-ink-faint">
            <IconSettings size={14} />
            Règles de trading actives
          </div>
          <div className="space-y-3">
            {RULESET_DISPLAY.map((rule) => (
              <div key={rule.label} className="flex items-center justify-between border-b border-paper-line pb-3 last:border-b-0">
                <span className="text-sm text-ink-soft">{rule.label}</span>
                <span className="font-mono text-sm tabular text-ink">{rule.value}</span>
              </div>
            ))}
          </div>
          <p className="mt-5 border-t border-paper-line pt-4 text-xs leading-relaxed text-ink-faint">
            Ces règles sont définies dans la configuration backend
            (app/config.py, table TradingRuleSet). L'édition depuis cette
            interface est une extension prévue mais non encore implémentée
            en V1.
          </p>
        </Card>

        <Card className="col-span-5">
          <div className="mb-4 text-xs uppercase tracking-[0.1em] text-ink-faint">À propos</div>
          <p className="text-sm leading-relaxed text-ink-soft">
            DOTOMI-TRADE recommande, valide et journalise — il n'exécute
            jamais d'ordre automatiquement. Toute statistique affichée dans
            ce produit provient de trades réellement journalisés ou d'un
            backtest réellement exécuté, jamais d'une estimation.
          </p>
        </Card>
      </div>
    </div>
  );
}
