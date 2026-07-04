import { IconCheck, IconClock, IconBlocked } from "../icons";
import { STATUS_COLOR_CLASS, STATUS_BG_CLASS, statusLabel } from "../lib/format";

const ICON_BY_STATUS = {
  AUTHORIZED: IconCheck,
  WATCH: IconClock,
  WEAK: IconClock,
  REJECTED: IconBlocked,
};

export function StatusBadge({ status, size = "md" }) {
  const Icon = ICON_BY_STATUS[status] || IconBlocked;
  const padding = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-3 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm border font-medium uppercase tracking-[0.08em] ${padding} ${STATUS_COLOR_CLASS[status] || "text-ink-soft"} ${STATUS_BG_CLASS[status] || "bg-paper-line/40 border-paper-line"}`}
    >
      <Icon size={size === "sm" ? 12 : 14} />
      {statusLabel(status)}
    </span>
  );
}
