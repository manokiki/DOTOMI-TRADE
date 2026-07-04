"""
Binance Provider — données OHLCV via REST public (sans clé API).
CORRIGÉ : le fichier original était vide.
"""

import logging
from datetime import datetime, timezone

import httpx
import pandas as pd

from app.config import settings
from app.data.base import MarketDataProvider

logger = logging.getLogger("dotomi.binance")

TIMEFRAME_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h", "1d": "1d",
}


class BinanceProvider(MarketDataProvider):
    name = "binance"

    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=settings.binance_base_url,
            timeout=10.0,
            headers={"User-Agent": "dotomi-trade/2.0"},
        )

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        tf = TIMEFRAME_MAP.get(timeframe, "1h")
        try:
            # Futures perpetuels en priorité
            resp = await self._client.get(
                "/fapi/v1/klines",
                params={"symbol": symbol, "interval": tf, "limit": limit},
            )
            resp.raise_for_status()
            return self._parse(resp.json())
        except Exception:
            # Fallback Spot
            resp = await self._client.get(
                "/api/v3/klines",
                params={"symbol": symbol, "interval": tf, "limit": limit},
            )
            resp.raise_for_status()
            return self._parse(resp.json())

    def _parse(self, raw: list) -> pd.DataFrame:
        rows = [
            {
                "timestamp": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                "open":   float(k[1]),
                "high":   float(k[2]),
                "low":    float(k[3]),
                "close":  float(k[4]),
                "volume": float(k[5]),
            }
            for k in raw
        ]
        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    async def get_funding_rate(self, symbol: str) -> float | None:
        try:
            resp = await self._client.get(
                "/fapi/v1/premiumIndex",
                params={"symbol": symbol},
            )
            resp.raise_for_status()
            return float(resp.json().get("lastFundingRate", 0))
        except Exception as e:
            logger.warning(f"funding_rate_failed symbol={symbol}: {e}")
            return None

    async def get_open_interest(self, symbol: str) -> float | None:
        try:
            resp = await self._client.get(
                "/fapi/v1/openInterest",
                params={"symbol": symbol},
            )
            resp.raise_for_status()
            return float(resp.json().get("openInterest", 0))
        except Exception as e:
            logger.warning(f"open_interest_failed symbol={symbol}: {e}")
            return None

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/api/v3/ping")
            return resp.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
