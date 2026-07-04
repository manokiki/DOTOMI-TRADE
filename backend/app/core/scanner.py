"""
Market Scanner — Version corrigée.

CORRECTIONS :
1. Appel MacroScanner avant le scoring
2. Lecture HumanCheckIn du jour avant validation
3. Archivage dans SystemTradeSignal
4. compute_score() reçoit macro
5. validate_setup() reçoit human_state + macro_context + vix
6. _persist_setup() écrit tous les nouveaux champs
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.alerting.email_alerts import send_trade_alert
from app.config import settings
from app.data.base import MarketDataProvider
from app.db.models import SystemHealthLog, SystemTradeSignal, TradeSetup, HumanCheckIn
from app.risk.risk_center import DailyRiskState, compute_position_size
from app.risk.validation import HumanState, validate_setup
from app.scoring.engine import ScoreResult, compute_score

logger = logging.getLogger("dotomi.scanner")

_macro_scanner_instance = None


def _get_macro_scanner():
    global _macro_scanner_instance
    if _macro_scanner_instance is None:
        from app.macro.macro_scanner import MacroScanner
        _macro_scanner_instance = MacroScanner()
    return _macro_scanner_instance


async def scan_symbol(
    provider: MarketDataProvider,
    symbol: str,
    timeframe: str,
    user_id: int,
    capital: float,
    risk_state: DailyRiskState,
    db: AsyncSession | None = None,
    send_alerts: bool = True,
) -> ScoreResult:
    """Pipeline complet : données → macro → score → human → validation → persist → alerte."""

    # 1. Données OHLCV
    raw_df = await provider.get_ohlcv(symbol, timeframe, limit=200)
    if raw_df.empty or len(raw_df) < 50:
        raise ValueError(f"Données insuffisantes pour {symbol} ({len(raw_df)} bougies)")

    _check_freshness(raw_df, symbol)

    # 2. Contexte macro
    macro = None
    try:
        macro = await _get_macro_scanner().get_full_macro()
    except Exception as e:
        logger.warning(f"macro_skipped: {e}")

    # 3. Score Engine (9 critères)
    score_result = compute_score(symbol, raw_df, macro=macro)

    # 4. État humain du jour
    human_state = HumanState()
    if db is not None:
        human_state = await _get_human_state(db)

    # 5. Validation Engine (22 conditions)
    vix       = getattr(macro, "vix", None) if macro else None
    macro_ctx = macro.context.value if macro and hasattr(macro.context, "value") else "NEUTRAL"

    validation = validate_setup(
        score_result, risk_state,
        human_state=human_state,
        macro_context=macro_ctx,
        vix=vix,
    )

    score_result.status = validation.final_status
    if validation.blocking_reasons:
        score_result.reasons = score_result.reasons + [
            f"Bloqué: {r}" for r in validation.blocking_reasons
        ]

    # 6. Sizing
    sizing = None
    if validation.is_authorized and score_result.entry_price and score_result.stop_loss:
        atr = None
        if "atr" in raw_df.columns:
            atr = float(raw_df.iloc[-1].get("atr", 0) or 0) or None
        sizing = compute_position_size(
            capital=capital,
            entry_price=score_result.entry_price,
            stop_loss=score_result.stop_loss,
            atr=atr,
            macro_context=macro_ctx,
        )

    # 7. Persistance
    if db is not None:
        await _persist_setup(db, user_id, timeframe, score_result, macro)
        await _persist_signal(db, score_result, macro)

    # 8. Alerte
    if send_alerts and validation.is_authorized:
        await send_trade_alert(score_result, sizing)

    logger.info(
        f"scan_ok symbol={symbol} score={score_result.total_score:.1f} "
        f"status={score_result.status} macro={macro_ctx} session={score_result.session_name}"
    )
    return score_result


def _check_freshness(df, symbol: str) -> None:
    last_ts = df.iloc[-1]["timestamp"]
    age = (datetime.now(timezone.utc) - last_ts).total_seconds()
    if age > settings.max_data_staleness_seconds:
        logger.warning(f"stale_data symbol={symbol} age={age:.0f}s")


async def _get_human_state(db: AsyncSession) -> HumanState:
    try:
        from sqlalchemy import select, desc
        today = datetime.now(timezone.utc).date().isoformat()
        stmt  = (
            select(HumanCheckIn)
            .where(HumanCheckIn.session_date == today)
            .order_by(desc(HumanCheckIn.created_at))
            .limit(1)
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            return HumanState(checkin_done=False)
        return HumanState(
            fatigue=row.fatigue, stress=row.stress,
            fomo=row.fomo, revenge_mode=row.revenge_mode,
            confidence=row.confidence, sleep_hours=row.sleep_hours,
            checkin_done=True,
        )
    except Exception as e:
        logger.warning(f"human_state_failed: {e}")
        return HumanState(checkin_done=False)


async def _persist_setup(db, user_id, timeframe, result: ScoreResult, macro) -> None:
    s = result.sub_scores
    setup = TradeSetup(
        user_id=user_id, symbol=result.symbol, direction=result.direction,
        timeframe=timeframe,
        regime_score=s.regime, structure_score=s.structure,
        liquidity_score=s.liquidity, pullback_score=s.pullback,
        timing_score=s.timing, confirmation_score=s.confirmation,
        risk_score=s.risk, total_score=result.total_score,
        score_macro=s.macro, score_onchain=s.onchain,
        entry_price=result.entry_price, stop_loss=result.stop_loss,
        tp1=result.tp1, tp2=result.tp2,
        entry_window_start=result.entry_window_start,
        entry_window_end=result.entry_window_end,
        status=result.status,
        reason="; ".join(result.reasons),
        macro_context=result.macro_context,
        fear_greed_value=getattr(getattr(macro, "fear_greed", None), "value", None) if macro else None,
        vix_value=getattr(macro, "vix", None) if macro else None,
        funding_rate_btc=getattr(getattr(macro, "onchain", None), "funding_rate_btc", None) if macro else None,
    )
    db.add(setup)
    await db.commit()


async def _persist_signal(db, result: ScoreResult, macro) -> None:
    try:
        s = result.sub_scores
        signal = SystemTradeSignal(
            symbol=result.symbol, direction=result.direction,
            total_score=result.total_score, status=result.status,
            score_regime=s.regime, score_structure=s.structure,
            score_liquidity=s.liquidity, score_pullback=s.pullback,
            score_timing=s.timing, score_confirm=s.confirmation,
            score_risk=s.risk, score_macro=s.macro, score_onchain=s.onchain,
            entry_price=result.entry_price, stop_loss=result.stop_loss,
            tp1=result.tp1, tp2=result.tp2, rrr=result.rrr,
            session_name=result.session_name,
            entry_window=f"{result.entry_window_start} – {result.entry_window_end}"
                if result.entry_window_start else None,
            macro_context=result.macro_context,
            fear_greed=getattr(getattr(macro, "fear_greed", None), "value", None) if macro else None,
            vix=getattr(macro, "vix", None) if macro else None,
            funding_rate=getattr(getattr(macro, "onchain", None), "funding_rate_btc", None) if macro else None,
            reasons=result.reasons,
        )
        db.add(signal)
        await db.commit()
    except Exception as e:
        logger.warning(f"signal_persist_failed: {e}")


async def record_health(db, component, status, latency_ms=None, error=None):
    log = SystemHealthLog(
        component=component, status=status,
        latency_ms=latency_ms, error_message=error,
    )
    db.add(log)
    await db.commit()
