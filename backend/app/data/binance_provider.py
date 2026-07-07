"""
Market Data Provider — Version corrigée.

CORRECTION CRITIQUE : Binance retourne 451 (bloc géographique) sur Railway/cloud.
Solution : Bybit comme provider principal, Binance en fallback local uniquement.

Bybit API publique fonctionne depuis tous les serveurs cloud sans restriction.
"""

import logging
from datetime import datetime, timezone

import httpx
import pandas as pd

from app.config import settings

logger = logging.getLogger("dotomi.provider")

TIMEFRAME_MAP = {
    "1m": "1",   "3m": "3",   "5m": "5",   "15m": "15",
    "30m": "30", "1h": "60",  "4h": "240", "1d": "D",
}

BYBIT_BASE = "https://api.bybit.com"
BINANCE_BASE = settings.binance_base_url


class BinanceProvider:
    """
    Provider principal : Bybit (pas de bloc cloud).
    Fallback : Binance (peut être bloqué sur Railway).
    """
    name = "bybit+binance"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": "DOTOMI-TRADE/2.0"},
        )

    async def get_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 200
    ) -> pd.DataFrame:
        """Bybit en priorité, Binance en fallback."""
        try:
            return await self._bybit_ohlcv(symbol, timeframe, limit)
        except Exception as e:
            logger.warning(f"bybit_failed symbol={symbol}: {e} — fallback Binance")
            return await self._binance_ohlcv(symbol, timeframe, limit)

    async def _bybit_ohlcv(
        self, symbol: str, timeframe: str, limit: int
    ) -> pd.DataFrame:
        """
        Bybit V5 API — fonctionne depuis Railway sans restriction.
        Endpoint : /v5/market/kline
        """
        interval = TIMEFRAME_MAP.get(timeframe, "60")
        resp = await self._client.get(
            f"{BYBIT_BASE}/v5/market/kline",
            params={
                "category": "linear",
                "symbol":   symbol,
                "interval": interval,
                "limit":    limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("retCode") != 0:
            raise ValueError(f"Bybit error: {data.get('retMsg')}")

        rows = []
        for k in reversed(data["result"]["list"]):
            # Bybit format: [startTime, open, high, low, close, volume, turnover]
            rows.append({
                "timestamp": datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc),
                "open":      float(k[1]),
                "high":      float(k[2]),
                "low":       float(k[3]),
                "close":     float(k[4]),
                "volume":    float(k[5]),
            })

        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    async def _binance_ohlcv(
        self, symbol: str, timeframe: str, limit: int
    ) -> pd.DataFrame:
        """Binance — fallback (peut être bloqué sur Railway)."""
        tf = timeframe  # Binance utilise "1h", "4h", etc.

        try:
            resp = await self._client.get(
                f"{BINANCE_BASE}/fapi/v1/klines",
                params={"symbol": symbol, "interval": tf, "limit": limit},
            )
            resp.raise_for_status()
            raw = resp.json()
        except Exception:
            resp = await self._client.get(
                f"{BINANCE_BASE}/api/v3/klines",
                params={"symbol": symbol, "interval": tf, "limit": limit},
            )
            resp.raise_for_status()
            raw = resp.json()

        rows = []
        for k in raw:
            rows.append({
                "timestamp": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                "open":      float(k[1]),
                "high":      float(k[2]),
                "low":       float(k[3]),
                "close":     float(k[4]),
                "volume":    float(k[5]),
            })

        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    async def get_funding_rate(self, symbol: str) -> float | None:
        """Funding rate via Bybit (sans restriction cloud)."""
        try:
            resp = await self._client.get(
                f"{BYBIT_BASE}/v5/market/tickers",
                params={"category": "linear", "symbol": symbol},
            )
            resp.raise_for_status()
            lst = resp.json().get("result", {}).get("list", [])
            if lst:
                return float(lst[0].get("fundingRate", 0)) * 100
        except Exception as e:
            logger.warning(f"bybit_funding_failed symbol={symbol}: {e}")
        return None

    async def get_open_interest(self, symbol: str) -> float | None:
        """Open interest via Bybit."""
        try:
            resp = await self._client.get(
                f"{BYBIT_BASE}/v5/market/open-interest",
                params={"category": "linear", "symbol": symbol, "intervalTime": "1h", "limit": 1},
            )
            resp.raise_for_status()
            lst = resp.json().get("result", {}).get("list", [])
            if lst:
                return float(lst[0].get("openInterest", 0))
        except Exception as e:
            logger.warning(f"bybit_oi_failed symbol={symbol}: {e}")
        return None

    async def health_check(self) -> bool:
        """Health check via Bybit (toujours accessible)."""
        try:
            resp = await self._client.get(f"{BYBIT_BASE}/v5/market/time")
            return resp.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
