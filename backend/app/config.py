"""
Configuration centrale DOTOMI-TRADE — Version corrigée.

CORRECTIONS appliquées par rapport à la version originale :
- min_rrr              : 1.5  → 2.5   (CDC section 9)
- max_daily_loss_pct   : 5.0  → 3.0   (CDC section 9)
- max_weekly_loss_pct  : 10.0 → 6.0   (CDC section 9)
- hard_safety_cap      : 10.0 → 3.0
- max_trades_per_day   : 5    → 3
- min_timing_score     : 40   → 60    (kill zone obligatoire)
- Ajout poids macro (5 pts) et onchain (5 pts)
- Ajout seuils kill zones UTC exacts
- Ajout seuils macro : DXY, VIX, Fear & Greed, funding rate
- Ajout clés API macro gratuites
- Ajout symbols_to_scan
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Base de données ---
    database_url: str = "sqlite+aiosqlite:///./dotomi_trade.db"

    # --- Données de marché ---
    binance_base_url: str = "https://api.binance.com"
    default_symbol: str = "BTCUSDT"
    default_timeframe: str = "1h"
    symbols_to_scan: str = "BTCUSDT,ETHUSDT,SOLUSDT"

    # --- APIs externes ---
    twelvedata_api_key: str = ""
    coinglass_api_key: str = ""
    cryptopanic_api_key: str = ""
    fred_api_key: str = ""

    # --- Pondération Score Engine — 9 critères (total = 100) ---
    weight_regime: float = 15.0
    weight_structure: float = 20.0
    weight_liquidity: float = 15.0
    weight_pullback: float = 10.0
    weight_timing: float = 10.0
    weight_confirmation: float = 10.0
    weight_risk: float = 10.0
    weight_macro: float = 5.0       # NOUVEAU
    weight_onchain: float = 5.0     # NOUVEAU

    # --- Seuils de statut ---
    threshold_authorized: float = 85.0
    threshold_watch: float = 70.0
    threshold_weak: float = 50.0

    # --- Seuils minimum sous-critères ---
    min_pullback_score: float = 50.0
    min_timing_score: float = 60.0   # CORRIGÉ : 40 → 60
    min_risk_score: float = 50.0
    min_rrr: float = 2.5             # CORRIGÉ : 1.5 → 2.5

    # --- Kill Zones UTC exactes (CORRECTIONS CRITIQUES) ---
    london_kz_start: int = 7         # 07h00 UTC
    london_kz_end: int = 10          # 10h00 UTC
    newyork_kz_start: int = 12       # 12h00 UTC
    newyork_kz_end: int = 15         # 15h00 UTC
    ny_close_start: int = 17         # 17h00 UTC
    ny_close_end: int = 19           # 19h00 UTC

    # --- Risk Management (CORRECTIONS CRITIQUES) ---
    default_capital: float = 100.0
    risk_pct_per_trade: float = 1.0
    atr_multiplier: float = 1.5
    max_daily_loss_pct: float = 3.0          # CORRIGÉ : 5.0 → 3.0
    max_weekly_loss_pct: float = 6.0         # CORRIGÉ : 10.0 → 6.0
    max_drawdown_absolute_pct: float = 15.0
    max_trades_per_day: int = 3              # CORRIGÉ : 5 → 3
    max_lever_standard: int = 10
    max_lever_conditional: int = 20
    hard_safety_cap_daily_loss_pct: float = 3.0  # CORRIGÉ : 10.0 → 3.0

    # --- Seuils macro ---
    dxy_hostile_threshold: float = 104.0
    dxy_favorable_threshold: float = 101.0
    vix_crisis_threshold: float = 35.0
    vix_hostile_threshold: float = 25.0
    vix_neutral_threshold: float = 20.0
    fear_greed_extreme_fear: int = 20
    fear_greed_extreme_greed: int = 80
    funding_rate_hot: float = 0.05

    # --- Monitoring ---
    max_data_staleness_seconds: int = 600
    retry_max_attempts: int = 5
    retry_base_delay_seconds: float = 1.0

    # --- Alerting ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_to: str = ""
    alerts_enabled: bool = False

    # --- Scheduler ---
    scheduler_enabled: bool = False

    # --- CORS ---
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
