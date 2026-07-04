"""
Connecteur Twelve Data — couvre forex et actions/indices sous une API
unique (section 3 du prompt maître : "si une seule API doit couvrir les
trois marchés... Twelve Data ou Polygon.io").

Nécessite une clé API (gratuite jusqu'à un certain volume de requêtes) —
contrairement à Binance, Twelve Data exige une authentification même pour
les données de base.

Implémente la même interface MarketDataProvider que BinanceProvider : le
Scanner et le Score Engine n'ont besoin d'aucune adaptation pour utiliser
ce connecteur à la place ou en complément de Binance.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
import pandas as pd

from app.config import settings
from app.data.base import MarketDataProvider
from app.data.binance_provider import CircuitBreaker

logger = logging.getLogger("dotomi.data.twelvedata")

# Twelve Data utilise sa propre convention d'intervalles.
_TIMEFRAME_MAP = {
    "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1h", "4h": "4h", "1d": "1day",
}


class TwelveDataProvider(MarketDataProvider):
    """
    Couvre le forex (ex: 'EUR/USD') et les actions/indices (ex: 'AAPL',
    'SPX'). Le symbole brut est transmis tel quel à l'API — c'est à
    l'appelant de respecter la convention de nommage Twelve Data.
    """

    name = "twelvedata"

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.twelvedata.com"):
        self.api_key = api_key or settings.twelvedata_api_key
        self.base_url = base_url
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)
        self._breaker = CircuitBreaker()

    async def _request_with_retry(self, path: str, params: dict) -> dict:
        if self._breaker.is_open:
            raise ConnectionError(
                f"[{self.name}] circuit breaker ouvert — source temporairement désactivée"
            )

        params = {**params, "apikey": self.api_key}
        last_exc: Exception | None = None
        for attempt in range(1, settings.retry_max_attempts + 1):
            try:
                response = await self._client.get(path, params=params)
                response.raise_for_status()
                data = response.json()
                # Twelve Data retourne un statut "error" dans le corps même
                # avec un code HTTP 200 — il faut le détecter explicitement.
                if isinstance(data, dict) and data.get("status") == "error":
                    raise ConnectionError(f"Erreur API Twelve Data : {data.get('message')}")
                self._breaker.record_success()
                return data
            except (httpx.HTTPError, httpx.TimeoutException, ConnectionError) as exc:
                last_exc = exc
                self._breaker.record_failure()
                delay = settings.retry_base_delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "twelvedata_request_failed",
                    extra={"attempt": attempt, "path": path, "delay": delay, "error": str(exc)},
                )
                if attempt < settings.retry_max_attempts:
                    await asyncio.sleep(delay)

        raise ConnectionError(
            f"[{self.name}] échec après {settings.retry_max_attempts} tentatives : {last_exc}"
        )

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        interval = _TIMEFRAME_MAP.get(timeframe, timeframe)
        data = await self._request_with_retry(
            "/time_series",
            params={"symbol": symbol, "interval": interval, "outputsize": limit},
        )

        values = data.get("values", [])
        rows = []
        for v in values:
            rows.append(
                {
                    "timestamp": pd.to_datetime(v["datetime"], utc=True),
                    "open": float(v["open"]),
                    "high": float(v["high"]),
                    "low": float(v["low"]),
                    "close": float(v["close"]),
                    "volume": float(v.get("volume", 0) or 0),
                }
            )

        # Twelve Data retourne le plus récent en premier -> on retrie en croissant.
        df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
        return df

    async def health_check(self) -> bool:
        try:
            await self._request_with_retry("/api_usage", params={})
            return True
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
