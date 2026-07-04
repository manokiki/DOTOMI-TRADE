import { IconArrowUp, IconArrowDown } from "../icons";
import { StatusBadge } from "./StatusBadge";
import { formatPrice, formatScore } from "../lib/format";

export function SetupRow({ setup, rank, onClick }) {
  const isBuy = setup.direction === "BUY";
  const DirIcon = isBuy ? IconArrowUp : IconArrowDown;
  const dirColor = isBuy ? "text-signal-authorized" : "text-signal-rejected";

  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-4 border-b border-paper-line px-4 py-3.5 text-left transition-colors last:border-b-0 hover:bg-paper/60"
    >
      {rank !== undefined && (
        <span className="w-6 font-mono text-xs tabular text-ink-faint">
          {String(rank).padStart(2, "0")}
        </span>
      )}

      <div className="w-28 shrink-0">
        <div className="font-display text-sm font-medium text-ink">{setup.symbol}</div>
        <div className={`mt-0.5 flex items-center gap-1 text-xs ${dirColor}`}>
          <DirIcon size={12} />
          {setup.direction}
        </div>
      </div>

      <div className="flex-1">
        <div className="font-mono text-xs tabular text-ink-soft">
          entrée {formatPrice(setup.entry_price)} · stop {formatPrice(setup.stop_loss)}
        </div>
      </div>

      <div className="w-16 text-right font-mono text-sm tabular text-ink">
        {formatScore(setup.score ?? setup.total_score)}
      </div>

      <StatusBadge status={setup.status} size="sm" />
    </button>
  );
}
