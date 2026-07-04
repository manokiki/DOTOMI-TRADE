/**
 * Icônes SVG dessinées sur mesure pour DOTOMI-TRADE.
 *
 * Contrainte explicite du projet : aucun émoji, nulle part dans
 * l'interface. Pas non plus de librairie d'icônes générique (lucide,
 * heroicons...) — chaque icône est tracée à la main en trait fin (1.5px),
 * cohérente avec l'identité visuelle "instrument de précision" du reste de
 * l'interface (cadrans, aiguilles, hairlines).
 *
 * Toutes acceptent `className` et `size` pour s'intégrer avec Tailwind.
 */

const base = (size) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
});

export function IconGauge({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M4 14a8 8 0 1 1 16 0" />
      <path d="M12 14 16 9" />
      <circle cx="12" cy="14" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconArrowUp({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 19V5" />
      <path d="M6 11l6-6 6 6" />
    </svg>
  );
}

export function IconArrowDown({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 5v14" />
      <path d="M18 13l-6 6-6-6" />
    </svg>
  );
}

export function IconShield({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
      <path d="M9.5 12l1.8 1.8L14.5 10" />
    </svg>
  );
}

export function IconBlocked({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M6.5 6.5l11 11" />
    </svg>
  );
}

export function IconJournal({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M6 3.5h10a1.5 1.5 0 0 1 1.5 1.5v15a1 1 0 0 1-1.5.87L12 19l-4 1.87A1 1 0 0 1 6.5 20V5A1.5 1.5 0 0 1 6 3.5z" />
      <path d="M9 8h6M9 11.5h6M9 15h4" />
    </svg>
  );
}

export function IconChart({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M4 19h16" />
      <path d="M7 19V9M12 19V5M17 19v-7" />
    </svg>
  );
}

export function IconScan({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8" />
      <path d="M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8" />
      <path d="M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16" />
      <path d="M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" />
      <circle cx="12" cy="12" r="3.2" />
    </svg>
  );
}

export function IconRiskCenter({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 2.5l8 3.2v5.3c0 5.2-3.4 8.6-8 10.5-4.6-1.9-8-5.3-8-10.5V5.7l8-3.2z" />
      <path d="M12 8v5" />
      <circle cx="12" cy="16" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconPlaybook({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <rect x="4" y="3.5" width="16" height="17" rx="1.5" />
      <path d="M9 3.5v17" />
      <path d="M13 9l3 2.5-3 2.5" />
    </svg>
  );
}

export function IconAlerts({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 3l9 16H3l9-16z" />
      <path d="M12 10v3.5" />
      <circle cx="12" cy="16.4" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconSettings({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.2M12 18.8V21M4.4 7.5l1.9 1.1M17.7 15.4l1.9 1.1M3 12h2.2M18.8 12H21M4.4 16.5l1.9-1.1M17.7 8.6l1.9-1.1" />
    </svg>
  );
}

export function IconClock({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

export function IconPulse({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M3 12h3.5l2-5 3 10 2-7 1.5 2H21" />
    </svg>
  );
}

export function IconLayers({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 3.5l8 4.3-8 4.3-8-4.3 8-4.3z" />
      <path d="M4 12l8 4.3 8-4.3" />
      <path d="M4 16l8 4.3 8-4.3" />
    </svg>
  );
}

export function IconCheck({ size = 20, className = "" }) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M5 12.5l4.5 4.5L19 7" />
    </svg>
  );
}
