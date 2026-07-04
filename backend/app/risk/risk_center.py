"""
Risk Center — Version corrigée.

Noms de champs IDENTIQUES à l'original (daily_pnl, weekly_pnl,
trades_taken_today) pour compatibilité avec scanner.py et scheduler.py.

CORRECTIONS :
- max_daily_loss_pct  : 3%   (était 5%)
- max_weekly_loss_pct : 6%   (était 10%)
- min_rrr             : 2.5  (était 1.5)
- Formule sizing exacte du CDC
- Ajustement levier selon contexte macro
- Courbe de capital cible 12 mois
"""

from dataclasses import dataclass

from app.config import settings


@dataclass
class PositionSizing:
    quantity:              float
    risk_amount:           float
    risk_pct_used:         float
    method_used:           str
    capped_by_safety_limit: bool


@dataclass
class DailyRiskState:
    capital:             float
    daily_pnl:           float = 0.0
    weekly_pnl:          float = 0.0
    trades_taken_today:  int   = 0
    consecutive_losses:  int   = 0
    session_blocked:     bool  = False
    block_reason:        str   = ""

    @property
    def daily_loss_pct(self) -> float:
        return max(0.0, -self.daily_pnl) / self.capital * 100 if self.capital > 0 else 0.0

    @property
    def weekly_loss_pct(self) -> float:
        return max(0.0, -self.weekly_pnl) / self.capital * 100 if self.capital > 0 else 0.0

    @property
    def risk_per_trade_usd(self) -> float:
        return self.capital * (settings.risk_pct_per_trade / 100)

    @property
    def daily_remaining_risk_usd(self) -> float:
        max_daily = self.capital * settings.max_daily_loss_pct / 100
        return max(0.0, max_daily - max(0.0, -self.daily_pnl))


def check_daily_limits(state: DailyRiskState) -> list[str]:
    blocks = []
    if state.session_blocked:
        blocks.append(f"Session bloquée : {state.block_reason}")
        return blocks
    if state.daily_loss_pct >= settings.max_daily_loss_pct:
        blocks.append(f"Limite journalière ({state.daily_loss_pct:.2f}% >= {settings.max_daily_loss_pct}%)")
    if state.weekly_loss_pct >= settings.max_weekly_loss_pct:
        blocks.append(f"Limite hebdomadaire ({state.weekly_loss_pct:.2f}% >= {settings.max_weekly_loss_pct}%)")
    if state.trades_taken_today >= settings.max_trades_per_day:
        blocks.append(f"Max {settings.max_trades_per_day} trades/jour atteint")
    if state.consecutive_losses >= 3:
        blocks.append("3 stops consécutifs — analyse obligatoire")
    return blocks


def compute_position_size(
    capital: float,
    entry_price: float,
    stop_loss: float,
    atr: float | None = None,
    risk_pct: float | None = None,
    macro_context: str = "NEUTRAL",
) -> PositionSizing:
    """
    Formule exacte CDC :
      distance_pct  = abs(entry - stop) / entry
      risque_usd    = capital * 0.01
      position_size = risque_usd / distance_pct
    """
    risk_pct = risk_pct if risk_pct is not None else settings.risk_pct_per_trade
    capped   = False

    if risk_pct > settings.hard_safety_cap_daily_loss_pct:
        risk_pct = settings.hard_safety_cap_daily_loss_pct
        capped   = True

    if macro_context == "HOSTILE":
        risk_pct *= 0.5
    elif macro_context == "CRISIS":
        return PositionSizing(0.0, 0.0, 0.0, "blocked_crisis", True)

    risk_usd   = capital * (risk_pct / 100.0)
    stop_dist  = abs(entry_price - stop_loss)
    if stop_dist <= 0:
        raise ValueError("Distance stop nulle")

    qty    = risk_usd / stop_dist
    method = "stop_distance"

    if atr and atr > 0:
        qty_atr = risk_usd / (atr * settings.atr_multiplier)
        if qty_atr < qty:
            qty    = qty_atr
            method = "atr"

    max_pos = capital * settings.max_lever_standard
    if qty * entry_price > max_pos:
        qty    = max_pos / entry_price
        method = method + "_capped"
        capped = True

    return PositionSizing(
        quantity=qty,
        risk_amount=risk_usd,
        risk_pct_used=risk_pct,
        method_used=method,
        capped_by_safety_limit=capped,
    )


# ── Courbe de capital cible ────────────────────────────────────────────────────

CAPITAL_CURVE = [
    {"month": 0,  "target": 100.0},
    {"month": 1,  "target": 138.0},
    {"month": 2,  "target": 190.0},
    {"month": 3,  "target": 261.0},
    {"month": 4,  "target": 359.0},
    {"month": 5,  "target": 494.0},
    {"month": 6,  "target": 680.0},
    {"month": 7,  "target": 935.0},
    {"month": 8,  "target": 1287.0},
    {"month": 9,  "target": 1771.0},
    {"month": 10, "target": 2436.0},
    {"month": 11, "target": 3352.0},
    {"month": 12, "target": 4613.0},
]
