export function Card({ children, className = "" }) {
  return (
    <div className={`rounded-sm border border-paper-line bg-paper-card p-5 ${className}`}>
      {children}
    </div>
  );
}

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="mb-6 flex items-start justify-between border-b border-paper-line pb-5">
      <div>
        <h1 className="font-display text-2xl font-medium tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-sm border border-dashed border-paper-line py-16 text-center">
      {Icon && <Icon size={28} className="text-ink-faint" />}
      <div className="font-display text-base text-ink">{title}</div>
      {description && <p className="max-w-sm text-sm text-ink-soft">{description}</p>}
    </div>
  );
}

export function ErrorBanner({ message }) {
  return (
    <div className="flex items-center gap-2.5 rounded-sm border border-signal-rejected/30 bg-signal-rejected/5 px-4 py-3 text-sm text-signal-rejected">
      {message}
    </div>
  );
}

export function Stat({ label, value, suffix, valueClassName = "" }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-[0.1em] text-ink-faint">{label}</div>
      <div className={`mt-1 font-mono text-lg tabular text-ink ${valueClassName}`}>
        {value}
        {suffix && <span className="ml-1 text-xs text-ink-soft">{suffix}</span>}
      </div>
    </div>
  );
}
