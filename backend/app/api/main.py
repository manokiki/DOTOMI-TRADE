"""
API FastAPI DOTOMI-TRADE — Version corrigée et complète.

CORRECTIONS :
- Import session : app.db.session (corrigé)
- Tous les nouveaux endpoints ajoutés
- Scanner intègre macro + human state
- Rétro-compatible avec tous les endpoints existants
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.scanner import _get_macro_scanner, scan_symbol
from app.core.scheduler import default_targets, run_scan_loop
from app.data.binance_provider import BinanceProvider
from app.data.registry import build_default_registry
from app.db.models import (
    HumanCheckIn, MacroSnapshot, SystemTradeSignal,
    Trade, TradeSetup, SystemHealthLog,
)
from app.db.session import AsyncSessionLocal, init_db
from app.risk.risk_center import CAPITAL_CURVE, DailyRiskState, compute_position_size
from app.risk.validation import HumanState, validate_setup
from app.scoring.engine import ScoreResult, SubScores

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("dotomi.api")

provider         = BinanceProvider()
DEFAULT_USER_ID  = 1
_scheduler_task  = None
_scheduler_stop  = None
_market_registry = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_task, _scheduler_stop, _market_registry
    await init_db()
    logger.info("startup_complete")

    if settings.scheduler_enabled:
        _market_registry = build_default_registry()
        _scheduler_stop  = asyncio.Event()
        _scheduler_task  = asyncio.create_task(
            run_scan_loop(_market_registry, default_targets(), stop_event=_scheduler_stop)
        )
        logger.info("scheduler_started")

    yield

    if _scheduler_stop:  _scheduler_stop.set()
    if _scheduler_task:  await asyncio.wait_for(_scheduler_task, timeout=10)
    if _market_registry: await _market_registry.aclose_all()
    await provider.aclose()
    logger.info("shutdown_complete")


app = FastAPI(
    title="DOTOMI-TRADE API",
    version="2.0.0",
    description="Système de décision trading — 100 USD → 4 000 USD en 12 mois",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_allowed_origins.split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    ok = await provider.health_check()
    return {"status": "ok" if ok else "degraded", "version": "2.0.0",
            "market_data_reachable": ok, "scheduler_enabled": settings.scheduler_enabled}


@app.get("/health/markets")
async def health_markets():
    if _market_registry is None:
        return {"scheduler_enabled": False, "markets": {}}
    return {"scheduler_enabled": True, "markets": await _market_registry.health_check_all()}


@app.get("/health/system")
async def health_system(hours: int = 24, db: AsyncSession = Depends(get_db)):
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt  = select(SystemHealthLog).where(SystemHealthLog.timestamp >= since).order_by(desc(SystemHealthLog.timestamp))
    rows  = (await db.execute(stmt)).scalars().all()
    by_c: dict = {}
    for r in rows:
        c = by_c.setdefault(r.component, {"ok": 0, "down": 0, "last_status": None, "last_error": None})
        if c["last_status"] is None:
            c["last_status"] = r.status
            c["last_error"]  = r.error_message
        c["ok" if r.status == "OK" else "down"] += 1
    return {"window_hours": hours, "components": by_c}


# ── Scanner ───────────────────────────────────────────────────────────────────

@app.get("/scanner")
async def get_scanner(
    symbol:    str = settings.default_symbol,
    timeframe: str = settings.default_timeframe,
    db: AsyncSession = Depends(get_db),
):
    state = DailyRiskState(capital=settings.default_capital)
    try:
        result = await scan_symbol(provider, symbol, timeframe,
                                   DEFAULT_USER_ID, settings.default_capital, state, db=db)
    except (ValueError, ConnectionError) as e:
        raise HTTPException(503, str(e))
    return _ser(result)


@app.get("/scanner/all")
async def scan_all(timeframe: str = "1h", db: AsyncSession = Depends(get_db)):
    symbols = [s.strip() for s in settings.symbols_to_scan.split(",")]
    results = []
    for sym in symbols:
        try:
            state = DailyRiskState(capital=settings.default_capital)
            r = await scan_symbol(provider, sym, timeframe,
                                   DEFAULT_USER_ID, settings.default_capital, state, db=db)
            results.append(_ser(r))
        except Exception as e:
            logger.warning(f"scan_failed sym={sym}: {e}")
    return sorted(results, key=lambda x: x["score"], reverse=True)


# ── Recommendations ───────────────────────────────────────────────────────────

@app.get("/recommendations/top")
async def top_recommendation(db: AsyncSession = Depends(get_db)):
    stmt = select(TradeSetup).order_by(desc(TradeSetup.total_score)).limit(3)
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        raise HTTPException(404, "Aucun setup enregistré")
    return {"top": _ser_setup(rows[0]), "alternatives": [_ser_setup(r) for r in rows[1:]]}


# ── Macro ─────────────────────────────────────────────────────────────────────

@app.get("/macro")
async def get_macro():
    try:
        m = await _get_macro_scanner().get_full_macro()
        return {
            "context": m.context.value,
            "macro_score": m.macro_score,
            "fear_greed": {"value": m.fear_greed.value, "classification": m.fear_greed.classification},
            "dxy": m.dxy, "vix": m.vix, "sp500_change_pct": m.sp500_change_pct,
            "funding_rate_btc": m.onchain.funding_rate_btc,
            "funding_rate_eth": m.onchain.funding_rate_eth,
            "news_sentiment": m.news_sentiment,
            "has_high_impact_event": m.has_high_impact_event_soon,
            "next_event": m.next_event_name,
            "next_event_hours": m.next_event_hours,
        }
    except Exception as e:
        raise HTTPException(503, f"Macro scanner indisponible: {e}")


# ── Risk ──────────────────────────────────────────────────────────────────────

class SizingRequest(BaseModel):
    capital:       float
    entry_price:   float
    stop_loss:     float
    max_leverage:  int   = 10
    macro_context: str   = "NEUTRAL"


@app.post("/risk/sizing")
async def compute_sizing(req: SizingRequest):
    try:
        r = compute_position_size(req.capital, req.entry_price, req.stop_loss,
                                  macro_context=req.macro_context)
        dist_pct = abs(req.entry_price - req.stop_loss) / req.entry_price * 100
        return {
            "capital": req.capital,
            "risk_usd": round(req.capital * settings.risk_pct_per_trade / 100, 4),
            "quantity": round(r.quantity, 6),
            "risk_amount": round(r.risk_amount, 4),
            "risk_pct": round(r.risk_pct_used, 3),
            "distance_stop_pct": round(dist_pct, 4),
            "position_usd": round(r.quantity * req.entry_price, 2),
            "method": r.method_used,
            "macro_context": req.macro_context,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/risk/summary")
async def risk_summary(capital: float = settings.default_capital,
                       db: AsyncSession = Depends(get_db)):
    today = date.today().isoformat()
    t_cnt = (await db.execute(select(func.count(Trade.id)).where(func.date(Trade.opened_at) == today))).scalar_one_or_none() or 0
    d_pnl = (await db.execute(select(func.sum(Trade.pnl)).where(func.date(Trade.opened_at) == today, Trade.pnl.is_not(None)))).scalar_one_or_none() or 0.0
    state = DailyRiskState(capital=capital, daily_pnl=d_pnl, trades_taken_today=t_cnt)
    return {
        "capital": capital,
        "risk_per_trade_usd": round(state.risk_per_trade_usd, 4),
        "daily_pnl": round(d_pnl, 4),
        "daily_loss_pct": round(state.daily_loss_pct, 3),
        "daily_remaining_risk_usd": round(state.daily_remaining_risk_usd, 4),
        "max_daily_loss_pct": settings.max_daily_loss_pct,
        "max_weekly_loss_pct": settings.max_weekly_loss_pct,
        "trades_today": t_cnt,
        "max_trades_per_day": settings.max_trades_per_day,
        "session_blocked": state.session_blocked,
    }


@app.get("/capital/curve")
async def capital_curve(db: AsyncSession = Depends(get_db)):
    total_pnl    = (await db.execute(select(func.sum(Trade.pnl)).where(Trade.pnl.is_not(None)))).scalar_one_or_none() or 0.0
    capital_real = settings.default_capital + total_pnl
    return {
        "capital_start":   settings.default_capital,
        "capital_current": round(capital_real, 2),
        "target_curve":    CAPITAL_CURVE,
        "total_pnl":       round(total_pnl, 2),
        "progress_pct":    round((capital_real - settings.default_capital) / (4000 - settings.default_capital) * 100, 1),
    }


# ── Human Check-in ────────────────────────────────────────────────────────────

class CheckInRequest(BaseModel):
    fatigue:      int
    stress:       int
    fomo:         bool
    revenge_mode: bool
    confidence:   int
    sleep_hours:  float
    notes:        str | None = None


@app.post("/human/checkin")
async def create_checkin(req: CheckInRequest, db: AsyncSession = Depends(get_db)):
    today  = date.today().isoformat()
    blocks = []
    if req.fatigue >= 8:    blocks.append(f"Fatigue {req.fatigue}/10")
    if req.stress >= 8:     blocks.append(f"Stress {req.stress}/10")
    if req.fomo:            blocks.append("FOMO actif")
    if req.revenge_mode:    blocks.append("Revenge mode")
    if req.confidence < 4:  blocks.append(f"Confiance {req.confidence}/10")
    if req.sleep_hours < 5: blocks.append(f"Sommeil {req.sleep_hours}h")

    rec = HumanCheckIn(
        session_date=today,
        fatigue=req.fatigue, stress=req.stress,
        fomo=req.fomo, revenge_mode=req.revenge_mode,
        confidence=req.confidence, sleep_hours=req.sleep_hours,
        notes=req.notes,
        session_blocked=len(blocks) > 0,
        block_reason="; ".join(blocks) if blocks else None,
    )
    db.add(rec); await db.commit(); await db.refresh(rec)
    return {"id": rec.id, "session_date": today,
            "session_blocked": rec.session_blocked, "block_reasons": blocks}


@app.get("/human/checkin/today")
async def today_checkin(db: AsyncSession = Depends(get_db)):
    today = date.today().isoformat()
    stmt  = select(HumanCheckIn).where(HumanCheckIn.session_date == today).order_by(desc(HumanCheckIn.created_at)).limit(1)
    row   = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        return {"checkin_done": False, "session_blocked": False}
    return {
        "checkin_done": True, "session_blocked": row.session_blocked,
        "block_reason": row.block_reason,
        "fatigue": row.fatigue, "stress": row.stress,
        "fomo": row.fomo, "revenge_mode": row.revenge_mode,
        "confidence": row.confidence, "sleep_hours": row.sleep_hours,
        "notes": row.notes,
    }


# ── Validation ────────────────────────────────────────────────────────────────

@app.post("/setup/validate")
async def validate_existing_setup(setup_id: int, db: AsyncSession = Depends(get_db)):
    setup = (await db.execute(select(TradeSetup).where(TradeSetup.id == setup_id))).scalar_one_or_none()
    if setup is None:
        raise HTTPException(404, "Setup introuvable")

    today   = date.today().isoformat()
    checkin = (await db.execute(select(HumanCheckIn).where(HumanCheckIn.session_date == today).limit(1))).scalar_one_or_none()
    human   = HumanState(
        fatigue=checkin.fatigue if checkin else 0,
        stress=checkin.stress if checkin else 0,
        fomo=checkin.fomo if checkin else False,
        revenge_mode=checkin.revenge_mode if checkin else False,
        confidence=checkin.confidence if checkin else 7,
        sleep_hours=checkin.sleep_hours if checkin else 8.0,
        checkin_done=checkin is not None,
    )

    sr = ScoreResult(
        symbol=setup.symbol, direction=setup.direction or "NONE",
        sub_scores=SubScores(
            regime=setup.regime_score or 0, structure=setup.structure_score or 0,
            liquidity=setup.liquidity_score or 0, pullback=setup.pullback_score or 0,
            timing=setup.timing_score or 0, confirmation=setup.confirmation_score or 0,
            risk=setup.risk_score or 0,
            macro=setup.score_macro or 0, onchain=setup.score_onchain or 0,
        ),
        total_score=setup.total_score or 0, status=setup.status or "REJECTED",
        entry_price=setup.entry_price, stop_loss=setup.stop_loss,
        tp1=setup.tp1, tp2=setup.tp2,
        rrr=(abs(setup.tp1 - setup.entry_price) / abs(setup.entry_price - setup.stop_loss)
             if setup.tp1 and setup.entry_price and setup.stop_loss and setup.entry_price != setup.stop_loss
             else None),
        reasons=[], macro_context=setup.macro_context or "NEUTRAL",
    )

    state  = DailyRiskState(capital=settings.default_capital)
    result = validate_setup(sr, state, human, macro_context=setup.macro_context or "NEUTRAL")
    return {
        "setup_id": setup_id, "symbol": setup.symbol,
        "is_authorized": result.is_authorized, "final_status": result.final_status,
        "conditions_checked": result.conditions_checked,
        "conditions_passed": result.conditions_passed,
        "blocking_reasons": result.blocking_reasons,
        "warnings": result.warnings,
    }


# ── Trade Journal ─────────────────────────────────────────────────────────────

@app.post("/trade/open")
async def open_trade(
    setup_id: int, quantity: float, entry_price: float, stop_loss: float,
    db: AsyncSession = Depends(get_db),
):
    setup = (await db.execute(select(TradeSetup).where(TradeSetup.id == setup_id))).scalar_one_or_none()
    if setup is None:
        raise HTTPException(404, "Setup introuvable")

    today   = date.today().isoformat()
    checkin = (await db.execute(select(HumanCheckIn).where(HumanCheckIn.session_date == today).limit(1))).scalar_one_or_none()

    trade = Trade(
        user_id=DEFAULT_USER_ID, setup_id=setup_id,
        symbol=setup.symbol, direction=setup.direction,
        entry_price=entry_price, stop_loss=stop_loss,
        quantity=quantity, risk_amount=abs(entry_price - stop_loss) * quantity,
        tp1=setup.tp1, tp2=setup.tp2,
        opened_at=datetime.now(timezone.utc), result="OPEN",
        total_score=setup.total_score, macro_context=setup.macro_context,
        human_fatigue=checkin.fatigue if checkin else None,
        human_stress=checkin.stress if checkin else None,
        human_confidence=checkin.confidence if checkin else None,
        human_sleep_hours=checkin.sleep_hours if checkin else None,
    )
    db.add(trade); await db.commit(); await db.refresh(trade)
    return {"trade_id": trade.id, "status": "opened"}


@app.post("/trade/close")
async def close_trade(
    trade_id: int, exit_price: float,
    note: str | None = None, error_tag: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    trade = (await db.execute(select(Trade).where(Trade.id == trade_id))).scalar_one_or_none()
    if trade is None:
        raise HTTPException(404, "Trade introuvable")

    mult         = 1 if trade.direction == "BUY" else -1
    trade.exit_price     = exit_price
    trade.pnl            = (exit_price - trade.entry_price) * mult * trade.quantity
    risk_unit    = abs(trade.entry_price - trade.stop_loss)
    trade.r_multiple     = trade.pnl / (risk_unit * trade.quantity) if risk_unit > 0 and trade.quantity else None
    trade.result         = "WIN" if trade.pnl > 0 else ("LOSS" if trade.pnl < 0 else "BREAKEVEN")
    trade.closed_at      = datetime.now(timezone.utc)
    trade.post_trade_note = note
    trade.error_tag      = error_tag

    await db.commit()
    return {"trade_id": trade.id, "pnl": trade.pnl,
            "r_multiple": trade.r_multiple, "result": trade.result}


@app.get("/journal")
async def get_journal(limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt   = select(Trade).where(Trade.user_id == DEFAULT_USER_ID).order_by(desc(Trade.opened_at)).limit(limit)
    trades = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": t.id, "symbol": t.symbol, "direction": t.direction,
            "entry_price": t.entry_price, "exit_price": t.exit_price,
            "stop_loss": t.stop_loss, "tp1": t.tp1, "tp2": t.tp2,
            "quantity": t.quantity, "pnl": t.pnl, "r_multiple": t.r_multiple,
            "result": t.result, "total_score": t.total_score,
            "macro_context": t.macro_context,
            "human_fatigue": t.human_fatigue, "human_stress": t.human_stress,
            "human_confidence": t.human_confidence,
            "post_trade_note": t.post_trade_note, "error_tag": t.error_tag,
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]


# ── Historique Système ────────────────────────────────────────────────────────

@app.get("/system/signals")
async def get_system_signals(
    limit: int = 100,
    status: str | None = None,
    symbol: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SystemTradeSignal).order_by(desc(SystemTradeSignal.signaled_at))
    if status: stmt = stmt.where(SystemTradeSignal.status == status.upper())
    if symbol: stmt = stmt.where(SystemTradeSignal.symbol == symbol.upper())
    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": s.id, "symbol": s.symbol, "direction": s.direction,
            "total_score": s.total_score, "status": s.status,
            "score_regime": s.score_regime, "score_structure": s.score_structure,
            "score_liquidity": s.score_liquidity, "score_pullback": s.score_pullback,
            "score_timing": s.score_timing, "score_confirm": s.score_confirm,
            "score_risk": s.score_risk, "score_macro": s.score_macro,
            "score_onchain": s.score_onchain,
            "entry_price": s.entry_price, "stop_loss": s.stop_loss,
            "tp1": s.tp1, "tp2": s.tp2, "rrr": s.rrr,
            "session_name": s.session_name, "entry_window": s.entry_window,
            "macro_context": s.macro_context, "fear_greed": s.fear_greed,
            "vix": s.vix, "funding_rate": s.funding_rate,
            "was_executed": s.was_executed, "trade_id": s.trade_id,
            "reasons": s.reasons,
            "signaled_at": s.signaled_at.isoformat() if s.signaled_at else None,
        }
        for s in rows
    ]


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/analytics")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    stmt   = select(Trade).where(Trade.user_id == DEFAULT_USER_ID, Trade.result.not_in(["OPEN"]), Trade.result.is_not(None))
    trades = (await db.execute(stmt)).scalars().all()
    if not trades:
        return {"trades_count": 0, "message": "Aucun trade clôturé"}

    wins     = [t for t in trades if t.result == "WIN"]
    losses   = [t for t in trades if t.result == "LOSS"]
    win_rate = len(wins) / len(trades) * 100
    r_vals   = [t.r_multiple for t in trades if t.r_multiple is not None]
    avg_r    = sum(r_vals) / len(r_vals) if r_vals else 0
    gp       = sum(t.pnl for t in wins if t.pnl)
    gl       = abs(sum(t.pnl for t in losses if t.pnl))
    expectancy = (win_rate / 100 * avg_r) - ((1 - win_rate / 100) * 1)

    human_perf: dict = {}
    for t in trades:
        if t.human_fatigue is not None:
            b = f"fatigue_{(t.human_fatigue // 3) * 3}"
            if b not in human_perf:
                human_perf[b] = {"trades": 0, "wins": 0, "total_r": 0.0}
            human_perf[b]["trades"] += 1
            if t.result == "WIN": human_perf[b]["wins"] += 1
            if t.r_multiple:      human_perf[b]["total_r"] += t.r_multiple

    return {
        "trades_count": len(trades),
        "win_count": len(wins), "loss_count": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "average_r_multiple": round(avg_r, 3),
        "total_pnl": round(sum(t.pnl for t in trades if t.pnl), 2),
        "profit_factor": round(gp / gl, 2) if gl > 0 else None,
        "expectancy_per_trade": round(expectancy, 3),
        "best_trade_r": round(max(r_vals), 3) if r_vals else None,
        "worst_trade_r": round(min(r_vals), 3) if r_vals else None,
        "human_performance": human_perf,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ser(r: ScoreResult) -> dict:
    return {
        "symbol": r.symbol, "direction": r.direction,
        "score": r.total_score, "status": r.status,
        "macro_context": r.macro_context,
        "session_name": r.session_name,
        "entry_window_start": r.entry_window_start,
        "entry_window_end": r.entry_window_end,
        "entry_price": r.entry_price, "stop_loss": r.stop_loss,
        "tp1": r.tp1, "tp2": r.tp2, "rrr": r.rrr,
        "reason": r.reasons,
        "sub_scores": {
            "regime": r.sub_scores.regime, "structure": r.sub_scores.structure,
            "liquidity": r.sub_scores.liquidity, "pullback": r.sub_scores.pullback,
            "timing": r.sub_scores.timing, "confirmation": r.sub_scores.confirmation,
            "risk": r.sub_scores.risk, "macro": r.sub_scores.macro,
            "onchain": r.sub_scores.onchain,
        },
    }


def _ser_setup(s: TradeSetup) -> dict:
    return {
        "id": s.id, "symbol": s.symbol, "direction": s.direction,
        "score": s.total_score, "status": s.status,
        "macro_context": s.macro_context,
        "entry_price": s.entry_price, "stop_loss": s.stop_loss,
        "tp1": s.tp1, "tp2": s.tp2,
        "reason": s.reason,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
