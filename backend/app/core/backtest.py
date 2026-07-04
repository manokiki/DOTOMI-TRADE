"""
Backtest — section 8 du prompt maître.

Rejoue le Score Engine sur un historique de données, simule le résultat de
chaque setup qui aurait été AUTHORIZED, et calcule les statistiques réelles
(taux de réussite, RRR moyen, expectancy, profit factor, drawdown max).

C'est la seule source légitime de chiffres de performance dans tout le
système — jamais une estimation théorique (garde-fou section 0 du prompt
maître).
"""

from dataclasses import dataclass

import pandas as pd

from app.config import settings
from app.risk.risk_center import DailyRiskState
from app.risk.validation import validate_setup
from app.scoring.engine import compute_score


@dataclass
class BacktestTradeResult:
    timestamp: pd.Timestamp
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    tp1: float
    outcome: str  # "TP1" / "STOP" / "TIMEOUT"
    r_multiple: float


@dataclass
class BacktestStats:
    total_setups_seen: int
    total_authorized: int
    trades_simulated: int
    win_rate_pct: float | None
    average_r_multiple: float | None
    profit_factor: float | None
    max_drawdown_r: float | None


def run_backtest(
    symbol: str,
    full_history: pd.DataFrame,
    lookback_window: int = 200,
    forward_window: int = 40,
) -> tuple[list[BacktestTradeResult], BacktestStats]:
    """
    Fait glisser une fenêtre de `lookback_window` bougies sur tout
    l'historique fourni. À chaque pas, calcule le score comme si on était
    "en direct" à cet instant (le Score Engine ne voit jamais le futur), et
    si le setup est AUTHORIZED, simule son issue sur les `forward_window`
    bougies suivantes (déjà connues dans l'historique, mais cachées du
    Score Engine au moment du calcul).

    C'est un backtest "walk-forward" simplifié, sans ré-optimisation des
    paramètres en cours de route — voir section 8 : l'objectif ici est de
    mesurer l'edge des formules actuelles, pas encore de les recalibrer
    automatiquement.
    """
    results: list[BacktestTradeResult] = []
    total_setups_seen = 0
    total_authorized = 0

    risk_state = DailyRiskState(capital=settings.default_capital, daily_pnl=0.0, weekly_pnl=0.0, trades_taken_today=0)

    for i in range(lookback_window, len(full_history) - forward_window):
        window = full_history.iloc[i - lookback_window : i].reset_index(drop=True)
        future = full_history.iloc[i : i + forward_window].reset_index(drop=True)

        try:
            score_result = compute_score(symbol, window)
        except Exception:
            continue

        total_setups_seen += 1
        validation = validate_setup(score_result, risk_state)

        if not validation.is_authorized:
            continue

        total_authorized += 1
        outcome, r_multiple = _simulate_outcome(score_result, future)
        results.append(
            BacktestTradeResult(
                timestamp=window.iloc[-1]["timestamp"],
                symbol=symbol,
                direction=score_result.direction,
                entry_price=score_result.entry_price,
                stop_loss=score_result.stop_loss,
                tp1=score_result.tp1,
                outcome=outcome,
                r_multiple=r_multiple,
            )
        )

    stats = _compute_stats(results, total_setups_seen, total_authorized)
    return results, stats


def _simulate_outcome(score_result, future: pd.DataFrame) -> tuple[str, float]:
    """
    Parcourt les bougies futures pour déterminer si le stop ou le TP1 est
    touché en premier. Si ni l'un ni l'autre dans la fenêtre, c'est un
    TIMEOUT (r_multiple = variation de prix au bout de la fenêtre, en
    unités de risque).
    """
    entry = score_result.entry_price
    stop = score_result.stop_loss
    tp1 = score_result.tp1
    direction = score_result.direction
    risk_distance = abs(entry - stop)

    if risk_distance <= 0:
        return "TIMEOUT", 0.0

    for _, candle in future.iterrows():
        if direction == "BUY":
            if candle["low"] <= stop:
                return "STOP", -1.0
            if candle["high"] >= tp1:
                r = (tp1 - entry) / risk_distance
                return "TP1", r
        else:
            if candle["high"] >= stop:
                return "STOP", -1.0
            if candle["low"] <= tp1:
                r = (entry - tp1) / risk_distance
                return "TP1", r

    last_close = future.iloc[-1]["close"]
    if direction == "BUY":
        r = (last_close - entry) / risk_distance
    else:
        r = (entry - last_close) / risk_distance
    return "TIMEOUT", r


def _compute_stats(results: list[BacktestTradeResult], total_seen: int, total_authorized: int) -> BacktestStats:
    if not results:
        return BacktestStats(
            total_setups_seen=total_seen,
            total_authorized=total_authorized,
            trades_simulated=0,
            win_rate_pct=None,
            average_r_multiple=None,
            profit_factor=None,
            max_drawdown_r=None,
        )

    wins = [r for r in results if r.r_multiple > 0]
    losses = [r for r in results if r.r_multiple <= 0]

    win_rate = len(wins) / len(results) * 100
    avg_r = sum(r.r_multiple for r in results) / len(results)

    gross_profit_r = sum(r.r_multiple for r in wins)
    gross_loss_r = abs(sum(r.r_multiple for r in losses))
    profit_factor = (gross_profit_r / gross_loss_r) if gross_loss_r > 0 else None

    # Drawdown max en unités R, sur la courbe d'équité cumulée des trades simulés.
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in results:
        cumulative += r.r_multiple
        peak = max(peak, cumulative)
        max_dd = max(max_dd, peak - cumulative)

    return BacktestStats(
        total_setups_seen=total_seen,
        total_authorized=total_authorized,
        trades_simulated=len(results),
        win_rate_pct=round(win_rate, 2),
        average_r_multiple=round(avg_r, 3),
        profit_factor=round(profit_factor, 2) if profit_factor else None,
        max_drawdown_r=round(max_dd, 2),
    )
