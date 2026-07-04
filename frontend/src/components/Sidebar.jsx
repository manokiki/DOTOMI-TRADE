/**
 * Sidebar.jsx — CORRIGÉ.
 * Ajout des liens Human Check-in et Historique Système.
 * Garde exactement le même style visuel que l'original.
 */
import { NavLink } from "react-router-dom";
import {
  IconGauge, IconScan, IconChart, IconShield,
  IconRiskCenter, IconJournal, IconPlaybook,
  IconAlerts, IconSettings, IconLayers,
} from "../icons";

// Icônes inline pour les 2 nouvelles pages
function IconHuman({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" />
    </svg>
  );
}

function IconSignals({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
      <path d="M4 6h16M4 12h10M4 18h13" />
    </svg>
  );
}

const NAV = [
  { to: "/",               label: "Dashboard",          icon: IconGauge,     end: true },
  { to: "/human",          label: "Check-in Session",   icon: IconHuman,     badge: "!" },
  { to: "/scanner",        label: "Scanner",            icon: IconScan },
  { to: "/recommendation", label: "Recommandation",     icon: IconChart },
  { to: "/validation",     label: "Validation",         icon: IconShield },
  { to: "/risk-center",    label: "Risk Center",        icon: IconRiskCenter },
  { to: "/signals",        label: "Historique Système", icon: IconSignals },
  { to: "/journal",        label: "Journal",            icon: IconJournal },
  { to: "/analytics",      label: "Analytics",          icon: IconLayers },
  { to: "/playbook",       label: "Playbook",           icon: IconPlaybook },
  { to: "/alerts",         label: "Alertes",            icon: IconAlerts },
  { to: "/settings",       label: "Profil & Règles",    icon: IconSettings },
];

export function Sidebar() {
  return (
    <aside className="flex h-screen w-60 flex-col border-r border-paper-line bg-paper-card">
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-paper-line px-5 py-5">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#173404" strokeWidth="1.5">
          <path d="M4 14a8 8 0 1 1 16 0" />
          <path d="M12 14 16 9" />
          <circle cx="12" cy="14" r="1" fill="#173404" stroke="none" />
        </svg>
        <div>
          <div className="font-display text-[15px] font-semibold leading-none tracking-tight text-ink">
            DOTOMI<span className="text-signal-authorized">-TRADE</span>
          </div>
          <div className="mt-0.5 text-[10px] uppercase tracking-[0.14em] text-ink-faint">
            Décision · Discipline
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2.5 py-4">
        {NAV.map(({ to, label, icon: Icon, end, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `mb-0.5 flex items-center gap-2.5 rounded-sm px-3 py-2 text-[13px] transition-colors ${
                isActive
                  ? "bg-signal-authorized/8 font-medium text-signal-authorized"
                  : "text-ink-soft hover:bg-paper/60 hover:text-ink"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span className={isActive ? "text-signal-authorized" : "text-ink-faint"}>
                  <Icon size={16} />
                </span>
                <span className="flex-1">{label}</span>
                {badge && !isActive && (
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-signal-watch/20 font-mono text-[9px] font-bold text-signal-watch">
                    {badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-paper-line px-5 py-4">
        <div className="text-[10px] text-ink-faint">Objectif 12 mois</div>
        <div className="font-mono text-sm font-medium text-ink">100 → 4 000 USD</div>
        <div className="mt-0.5 text-[10px] text-ink-faint">Exécution manuelle uniquement.</div>
      </div>
    </aside>
  );
}
