"""
Modèles SQLAlchemy — Version corrigée.

CORRECTIONS :
- TradingRuleSet : valeurs par défaut corrigées (3%/6%/2.5/3)
- TradeSetup     : ajout score_macro, score_onchain, macro_context, fear_greed_value, vix_value, funding_rate_btc
- Trade          : ajout champs humain, contexte, note post-trade, error_tag

NOUVEAUX MODÈLES :
- HumanCheckIn       : check-in humain avant chaque session
- SystemTradeSignal  : historique de tous les signaux du moteur
- MacroSnapshot      : snapshot macro horaire pour analytics
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    name          = Column(String,  nullable=False)
    email         = Column(String,  unique=True, nullable=False)
    password_hash = Column(String,  nullable=False)
    base_currency = Column(String,  default="USD")
    timezone      = Column(String,  default="UTC")
    created_at    = Column(DateTime, default=_now)
    updated_at    = Column(DateTime, default=_now, onupdate=_now)


class TradingRuleSet(Base):
    """CORRIGÉ : toutes les valeurs par défaut respectent le CDC."""
    __tablename__ = "trading_rule_sets"
    id                       = Column(Integer, primary_key=True)
    user_id                  = Column(Integer, nullable=False)
    max_risk_per_trade_pct   = Column(Float,   default=1.0)
    max_daily_loss_pct       = Column(Float,   default=3.0)    # CORRIGÉ : 5 → 3
    max_weekly_loss_pct      = Column(Float,   default=6.0)    # CORRIGÉ : 10 → 6
    max_trades_per_day       = Column(Integer, default=3)      # CORRIGÉ : 5 → 3
    min_rrr                  = Column(Float,   default=2.5)    # CORRIGÉ : 1.5 → 2.5
    min_recommendation_score = Column(Float,   default=85.0)
    allowed_sessions         = Column(String,  default="london,newyork")
    allowed_markets          = Column(String,  default="crypto")
    enabled                  = Column(Boolean, default=True)
    created_at               = Column(DateTime, default=_now)
    updated_at               = Column(DateTime, default=_now, onupdate=_now)


class MarketSnapshot(Base):
    __tablename__   = "market_snapshots"
    id              = Column(Integer, primary_key=True)
    symbol          = Column(String,  nullable=False, index=True)
    timeframe       = Column(String,  nullable=False)
    timestamp       = Column(DateTime, nullable=False, index=True)
    open            = Column(Float)
    high            = Column(Float)
    low             = Column(Float)
    close           = Column(Float)
    volume          = Column(Float)
    atr             = Column(Float)
    regime          = Column(String)
    trend_bias      = Column(String)
    liquidity_state = Column(String)
    structure_state = Column(String)
    session_state   = Column(String)


class TradeSetup(Base):
    """CORRIGÉ : ajout champs macro, onchain, session."""
    __tablename__      = "trade_setups"
    id                 = Column(Integer, primary_key=True)
    user_id            = Column(Integer, nullable=False)
    symbol             = Column(String,  nullable=False)
    direction          = Column(String)
    timeframe          = Column(String)
    regime_score       = Column(Float)
    structure_score    = Column(Float)
    liquidity_score    = Column(Float)
    pullback_score     = Column(Float)
    timing_score       = Column(Float)
    confirmation_score = Column(Float)
    risk_score         = Column(Float)
    total_score        = Column(Float)
    # Nouveaux scores
    score_macro        = Column(Float, default=0.0)
    score_onchain      = Column(Float, default=0.0)
    # Niveaux
    entry_price        = Column(Float)
    stop_loss          = Column(Float)
    tp1                = Column(Float)
    tp2                = Column(Float)
    invalidation_level = Column(Float)
    entry_window_start = Column(String)
    entry_window_end   = Column(String)
    # Contexte macro archivé
    macro_context      = Column(String, default="NEUTRAL")
    fear_greed_value   = Column(Integer)
    vix_value          = Column(Float)
    funding_rate_btc   = Column(Float)
    status             = Column(String)
    reason             = Column(Text)
    created_at         = Column(DateTime, default=_now)
    updated_at         = Column(DateTime, default=_now, onupdate=_now)


class Trade(Base):
    """CORRIGÉ : ajout état humain, contexte, note post-trade, error_tag."""
    __tablename__       = "trades"
    id                  = Column(Integer, primary_key=True)
    user_id             = Column(Integer, nullable=False)
    setup_id            = Column(Integer)
    symbol              = Column(String,  nullable=False)
    direction           = Column(String)
    entry_price         = Column(Float)
    exit_price          = Column(Float)
    stop_loss           = Column(Float)
    tp1                 = Column(Float)
    tp2                 = Column(Float)
    quantity            = Column(Float)
    risk_amount         = Column(Float)
    pnl                 = Column(Float)
    r_multiple          = Column(Float)
    opened_at           = Column(DateTime)
    closed_at           = Column(DateTime)
    result              = Column(String)   # WIN / LOSS / BREAKEVEN / OPEN
    # Contexte
    total_score         = Column(Float)
    macro_context       = Column(String)
    fear_greed_at_entry = Column(Integer)
    # État humain archivé
    human_fatigue       = Column(Integer)
    human_stress        = Column(Integer)
    human_confidence    = Column(Integer)
    human_sleep_hours   = Column(Float)
    # Journal
    notes               = Column(Text)
    post_trade_note     = Column(Text)
    error_tag           = Column(String(50))  # FOMO / REVENGE / LATE_ENTRY
    screenshot_url      = Column(String)


class HumanCheckIn(Base):
    """NOUVEAU — check-in humain obligatoire avant chaque session."""
    __tablename__   = "human_checkins"
    id              = Column(Integer, primary_key=True)
    session_date    = Column(String(20), nullable=False, index=True)
    fatigue         = Column(Integer, default=0)
    stress          = Column(Integer, default=0)
    fomo            = Column(Boolean, default=False)
    revenge_mode    = Column(Boolean, default=False)
    confidence      = Column(Integer, default=7)
    sleep_hours     = Column(Float,   default=8.0)
    notes           = Column(Text)
    session_blocked = Column(Boolean, default=False)
    block_reason    = Column(String(500))
    created_at      = Column(DateTime, default=_now)


class SystemTradeSignal(Base):
    """NOUVEAU — historique de TOUS les signaux, exécutés ou non."""
    __tablename__   = "system_trade_signals"
    id              = Column(Integer, primary_key=True)
    symbol          = Column(String(20), nullable=False, index=True)
    direction       = Column(String(10), nullable=False)
    total_score     = Column(Float,  nullable=False)
    status          = Column(String(20), nullable=False, index=True)
    score_regime    = Column(Float, default=0.0)
    score_structure = Column(Float, default=0.0)
    score_liquidity = Column(Float, default=0.0)
    score_pullback  = Column(Float, default=0.0)
    score_timing    = Column(Float, default=0.0)
    score_confirm   = Column(Float, default=0.0)
    score_risk      = Column(Float, default=0.0)
    score_macro     = Column(Float, default=0.0)
    score_onchain   = Column(Float, default=0.0)
    entry_price     = Column(Float)
    stop_loss       = Column(Float)
    tp1             = Column(Float)
    tp2             = Column(Float)
    rrr             = Column(Float)
    session_name    = Column(String(50))
    entry_window    = Column(String(50))
    macro_context   = Column(String(20), default="NEUTRAL")
    fear_greed      = Column(Integer)
    vix             = Column(Float)
    funding_rate    = Column(Float)
    was_executed    = Column(Boolean, default=False)
    trade_id        = Column(Integer)
    reasons         = Column(JSON, default=list)
    signaled_at     = Column(DateTime, default=_now, index=True)


class SessionReview(Base):
    __tablename__        = "session_reviews"
    id                   = Column(Integer, primary_key=True)
    user_id              = Column(Integer, nullable=False)
    date                 = Column(DateTime)
    daily_pnl            = Column(Float)
    max_drawdown         = Column(Float)
    trades_taken         = Column(Integer)
    trades_validated     = Column(Integer)
    trades_blocked       = Column(Integer)
    errors_count         = Column(Integer)
    best_setup_type      = Column(String)
    worst_setup_type     = Column(String)
    notes                = Column(Text)


class MacroSnapshot(Base):
    """Snapshot macro horaire pour analytics long terme."""
    __tablename__  = "macro_snapshots"
    id             = Column(Integer, primary_key=True)
    context        = Column(String(20), nullable=False)
    fear_greed     = Column(Integer)
    vix            = Column(Float)
    dxy            = Column(Float)
    sp500_change   = Column(Float)
    funding_btc    = Column(Float)
    funding_eth    = Column(Float)
    news_sentiment = Column(Float)
    macro_score    = Column(Float)
    snapped_at     = Column(DateTime, default=_now, index=True)


class SystemHealthLog(Base):
    __tablename__  = "system_health_logs"
    id             = Column(Integer, primary_key=True)
    component      = Column(String, nullable=False)
    status         = Column(String, nullable=False)
    latency_ms     = Column(Float)
    error_message  = Column(Text)
    timestamp      = Column(DateTime, default=_now)
