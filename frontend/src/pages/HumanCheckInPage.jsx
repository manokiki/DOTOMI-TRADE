/**
 * HumanCheckInPage — Check-in état humain obligatoire avant chaque session.
 * Compatible avec l'architecture existante (Layout, usePolling, api, StatusBadge).
 */
import { useState, useEffect } from "react";
import { PageHeader, Card, ErrorBanner } from "../components/Layout";
import { api } from "../lib/api";
import { usePolling } from "../lib/usePolling";

// ── Icônes ────────────────────────────────────────────────────────────────────
function IconOk({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none"
      stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="5.5" />
      <path d="M4.5 7l2 2L9.5 5.5" />
    </svg>
  );
}
function IconBlock({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none"
      stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
      <circle cx="7" cy="7" r="5.5" />
      <path d="M3.5 3.5l7 7" />
    </svg>
  );
}

// ── Composants ────────────────────────────────────────────────────────────────
function Slider({ label, value, onChange, max = 10, description, danger, warn }) {
  const pct   = (value / max) * 100;
  const color = danger(value) ? "bg-signal-rejected"
              : warn(value)   ? "bg-signal-watch"
              : "bg-signal-authorized";
  const text  = danger(value) ? "text-signal-rejected"
              : warn(value)   ? "text-signal-watch"
              : "text-signal-authorized";
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-ink">{label}</label>
        <span className={`font-mono text-lg font-semibold tabular ${text}`}>
          {value}<span className="text-xs font-normal text-ink-faint">/{max}</span>
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-paper-line">
        <div className={`absolute left-0 h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }} />
        <input type="range" min={0} max={max} step={max === 12 ? 0.5 : 1}
          value={value} onChange={e => onChange(Number(e.target.value))}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0" />
      </div>
      {description && <p className="text-[11px] text-ink-faint">{description}</p>}
    </div>
  );
}

function Toggle({ label, value, onChange, description }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <div className="text-sm font-medium text-ink">{label}</div>
        {description && <div className="mt-0.5 text-[11px] text-ink-faint">{description}</div>}
      </div>
      <button onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
          value ? "bg-signal-rejected" : "bg-paper-line"
        }`}>
        <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
          value ? "translate-x-6" : "translate-x-1"
        }`} />
      </button>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export function HumanCheckInPage() {
  const { data: existing } = usePolling(() => api.getTodayCheckIn(), { intervalMs: 60000 });

  const [fatigue,    setFatigue]    = useState(3);
  const [stress,     setStress]     = useState(3);
  const [confidence, setConfidence] = useState(7);
  const [sleep,      setSleep]      = useState(7);
  const [fomo,       setFomo]       = useState(false);
  const [revenge,    setRevenge]    = useState(false);
  const [notes,      setNotes]      = useState("");
  const [result,     setResult]     = useState(null);
  const [error,      setError]      = useState(null);
  const [loading,    setLoading]    = useState(false);

  useEffect(() => {
    if (existing?.checkin_done) {
      setFatigue(existing.fatigue      ?? 3);
      setStress(existing.stress        ?? 3);
      setConfidence(existing.confidence ?? 7);
      setSleep(existing.sleep_hours    ?? 7);
      setFomo(existing.fomo            ?? false);
      setRevenge(existing.revenge_mode ?? false);
      setNotes(existing.notes          ?? "");
    }
  }, [existing]);

  // Calcul live des blocages
  const blocks = [];
  if (fatigue >= 8)   blocks.push(`Fatigue ${fatigue}/10 — session bloquée`);
  if (stress >= 8)    blocks.push(`Stress ${stress}/10 — session bloquée`);
  if (fomo)           blocks.push("FOMO actif — toutes entrées interdites");
  if (revenge)        blocks.push("Revenge mode — session bloquée jusqu'à demain");
  if (confidence < 4) blocks.push(`Confiance ${confidence}/10 — aucun trade`);
  if (sleep < 5)      blocks.push(`Sommeil ${sleep}h — session bloquée`);

  const warnings = [];
  if (fatigue >= 6 && fatigue < 8)  warnings.push("Levier plafonné à 10x");
  if (stress >= 6 && stress < 8)    warnings.push("Risque réduit à 0.5%/trade");
  if (sleep >= 5 && sleep < 6)      warnings.push("Session limitée à 1h max");

  async function submit() {
    setError(null); setLoading(true);
    try {
      const data = await api.createCheckIn({
        fatigue, stress, fomo, revenge_mode: revenge,
        confidence, sleep_hours: sleep, notes,
      });
      setResult(data);
    } catch (e) {
      setError(e.message || "Erreur lors de l'enregistrement");
    } finally {
      setLoading(false);
    }
  }

  const today = new Date().toLocaleDateString("fr-FR", {
    weekday: "long", day: "numeric", month: "long",
  });

  return (
    <div>
      <PageHeader
        title="Check-in Session"
        subtitle={`État mental avant trading — ${today}`}
      />

      {existing?.checkin_done && !result && (
        <div className="mb-5 rounded-sm border border-paper-line bg-paper px-4 py-3 text-sm text-ink-soft">
          Check-in déjà effectué aujourd'hui. Modifiable ci-dessous.
        </div>
      )}

      <div className="grid grid-cols-12 gap-5">
        {/* Formulaire */}
        <div className="col-span-7 space-y-5">
          <Card>
            <div className="mb-4 text-[10px] uppercase tracking-[0.1em] text-ink-faint">État physique</div>
            <div className="space-y-6">
              <Slider label="Fatigue" value={fatigue} onChange={setFatigue}
                danger={v => v >= 8} warn={v => v >= 6}
                description=">= 8 : session bloquée. 6–7 : levier réduit à 10x." />
              <Slider label="Heures de sommeil" value={sleep} onChange={setSleep}
                max={12} danger={v => v < 5} warn={v => v < 6}
                description="< 5h : session bloquée. 5–6h : session limitée 1h." />
            </div>
          </Card>

          <Card>
            <div className="mb-4 text-[10px] uppercase tracking-[0.1em] text-ink-faint">État mental</div>
            <div className="space-y-6">
              <Slider label="Stress" value={stress} onChange={setStress}
                danger={v => v >= 8} warn={v => v >= 6}
                description=">= 8 : session bloquée. 6–7 : risque réduit à 0.5%." />
              <Slider label="Confiance" value={confidence} onChange={setConfidence}
                danger={v => v < 4} warn={v => v < 6}
                description="< 4 : aucun trade autorisé." />
            </div>
          </Card>

          <Card>
            <div className="mb-4 text-[10px] uppercase tracking-[0.1em] text-ink-faint">Biais émotionnels</div>
            <div className="space-y-5">
              <Toggle label="FOMO actif" value={fomo} onChange={setFomo}
                description="Peur de manquer — entrée interdite même si score = 100." />
              <Toggle label="Revenge mode" value={revenge} onChange={setRevenge}
                description="Envie de récupérer une perte. État le plus dangereux." />
            </div>
          </Card>

          <Card>
            <div className="mb-2 text-[10px] uppercase tracking-[0.1em] text-ink-faint">Note (optionnel)</div>
            <textarea value={notes} onChange={e => setNotes(e.target.value)}
              rows={3} placeholder="Comment vous sentez-vous pour cette session ?"
              className="w-full resize-none rounded-sm border border-paper-line bg-paper px-3 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:border-ink/40 focus:outline-none" />
          </Card>
        </div>

        {/* Panneau statut */}
        <div className="col-span-5 space-y-4">
          <Card>
            <div className="mb-3 text-[10px] uppercase tracking-[0.1em] text-ink-faint">Statut en direct</div>
            {blocks.length > 0 ? (
              <div className="rounded-sm border border-signal-rejected/30 bg-signal-rejected/5 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium text-signal-rejected">
                  <IconBlock /> Session bloquée
                </div>
                <ul className="space-y-1">
                  {blocks.map((b, i) => <li key={i} className="text-sm text-signal-rejected/80">— {b}</li>)}
                </ul>
              </div>
            ) : (
              <div className="rounded-sm border border-signal-authorized/30 bg-signal-authorized/5 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-signal-authorized">
                  <IconOk /> Session autorisée
                </div>
                <p className="mt-1 text-[11px] text-signal-authorized/70">
                  Toutes les conditions humaines sont réunies.
                </p>
              </div>
            )}
            {warnings.length > 0 && (
              <div className="mt-3 rounded-sm border border-signal-watch/30 bg-signal-watch/5 p-3">
                <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-signal-watch">Ajustements actifs</div>
                <ul className="space-y-1">
                  {warnings.map((w, i) => <li key={i} className="text-[11px] text-signal-watch/80">— {w}</li>)}
                </ul>
              </div>
            )}
          </Card>

          <Card>
            <div className="mb-3 text-[10px] uppercase tracking-[0.1em] text-ink-faint">Résumé</div>
            <div className="space-y-2.5">
              {[
                { label: "Fatigue",   val: `${fatigue}/10`,   d: fatigue >= 8,    w: fatigue >= 6 },
                { label: "Stress",    val: `${stress}/10`,    d: stress >= 8,     w: stress >= 6 },
                { label: "Confiance", val: `${confidence}/10`,d: confidence < 4,  w: confidence < 6 },
                { label: "Sommeil",   val: `${sleep}h`,       d: sleep < 5,       w: sleep < 6 },
                { label: "FOMO",      val: fomo ? "OUI":"NON",  d: fomo },
                { label: "Revenge",   val: revenge ? "OUI":"NON", d: revenge },
              ].map(({ label, val, d, w }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-sm text-ink-soft">{label}</span>
                  <span className={`font-mono text-sm font-medium tabular ${
                    d ? "text-signal-rejected" : w ? "text-signal-watch" : "text-signal-authorized"
                  }`}>{val}</span>
                </div>
              ))}
            </div>
          </Card>

          <button onClick={submit} disabled={loading}
            className="w-full rounded-sm bg-ink px-4 py-3 text-sm font-medium text-paper hover:opacity-90 disabled:opacity-40">
            {loading ? "Enregistrement..." : "Valider le check-in"}
          </button>

          {error && <ErrorBanner message={error} />}

          {result && (
            <div className={`rounded-sm border p-4 text-sm ${
              result.session_blocked
                ? "border-signal-rejected/30 bg-signal-rejected/5 text-signal-rejected"
                : "border-signal-authorized/30 bg-signal-authorized/5 text-signal-authorized"
            }`}>
              Check-in enregistré.{" "}
              {result.session_blocked
                ? `Session bloquée : ${result.block_reasons?.join(", ")}`
                : "Session autorisée — bonne discipline."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
