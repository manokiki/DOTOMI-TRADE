"""
Market Data Provider — Version corrigée.

PROBLÈME : Binance (451) ET Bybit (403) bloquent Railway (AWS us-east).
SOLUTION : CryptoCompare API (gratuit, sans clé, aucune restriction géographique).
Fallback : CoinGecko (gratuit, sans clé).
"""

import logging
from datetime import datetime, timezone

import httpx
import pandas as pd

from app.config import settings

logger = logging.getLogger("dotomi.provider")

# CryptoCompare — gratuit, sans clé, aucune restriction cloud
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com"

# CoinGecko — fallback gratuit
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Map timeframe → paramètres CryptoCompare
TIMEFRAME_MAP = {
    "1m":  ("histominute", 1),
    "5m":  ("histominute", 5),
    "15m": ("histominute", 15),
    "30m": ("histominute", 30),
    "1h":  ("histohour",   1),
    "4h":  ("histohour",   4),
    "1d":  ("histoday",    1),
}

# Map symboles USDT → symboles CryptoCompare
SYMBOL_MAP = {
    "BTCUSDT": ("BTC", "USDT"),
    "ETHUSDT": ("ETH", "USDT"),
    "SOLUSDT": ("SOL", "USDT"),
    "BNBUSDT": ("BNB", "USDT"),
    "AVAXUSDT": ("AVAX", "USDT"),
}


class BinanceProvider:
    """
    Provider de données de marché.
    Source principale : CryptoCompare (aucune restriction géographique).
    Fallback : CoinGecko.
    """
    name = "cryptocompare+coingecko"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": "DOTOMI-TRADE/2.0",
                "Accept": "application/json",
            },
        )

    async def get_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 200
    ) -> pd.DataFrame:
        try:
            return await self._cryptocompare_ohlcv(symbol, timeframe, limit)
        except Exception as e:
            logger.warning(f"cryptocompare_failed symbol={symbol}: {e} — fallback coingecko")
            return await self._coingecko_ohlcv(symbol, timeframe, limit)

    async def _cryptocompare_ohlcv(
        self, symbol: str, timeframe: str, limit: int
    ) -> pd.DataFrame:
        """
        CryptoCompare OHLCV — gratuit sans clé, 100 appels/sec.
        Endpoint : /data/v2/histominute ou histohour ou histoday
        """
        fsym, tsym = SYMBOL_MAP.get(symbol, (symbol.replace("USDT", ""), "USDT"))
        endpoint, aggregate = TIMEFRAME_MAP.get(timeframe, ("histohour", 1))

        resp = await self._client.get(
            f"{CRYPTOCOMPARE_BASE}/data/v2/{endpoint}",
            params={
                "fsym":      fsym,
                "tsym":      tsym,
                "limit":     min(limit, 2000),
                "aggregate": aggregate,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("Response") != "Success":
            raise ValueError(f"CryptoCompare error: {data.get('Message')}")

        rows = []
        for k in data["Data"]["Data"]:
            if k["open"] == 0 and k["close"] == 0:
                continue
            rows.append({
                "timestamp": datetime.fromtimestamp(k["time"], tz=timezone.utc),
                "open":      float(k["open"]),
                "high":      float(k["high"]),
                "low":       float(k["low"]),
                "close":     float(k["close"]),
                "volume":    float(k["volumefrom"]),
            })

        if not rows:
            raise ValueError("CryptoCompare retourné 0 bougies valides")

        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    async def _coingecko_ohlcv(
        self, symbol: str, timeframe: str, limit: int
    ) -> pd.DataFrame:
        """
        CoinGecko OHLCV — fallback gratuit.
        Résolution : 1h pour les 2 derniers jours, 4h pour 90 jours.
        """
        coin_map = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "SOLUSDT": "solana",
            "BNBUSDT": "binancecoin",
            "AVAXUSDT": "avalanche-2",
        }
        coin_id = coin_map.get(symbol, "bitcoin")

        # CoinGecko retourne des bougies sur une période
        days = 7 if timeframe in ("1m", "5m", "15m", "30m") else 30

        resp = await self._client.get(
            f"{COINGECKO_BASE}/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": days},
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
                "volume":    0.0,
            })

        if not rows:
            raise ValueError("CoinGecko retourné 0 bougies")

        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    async def get_funding_rate(self, symbol: str) -> float | None:
        """
        Funding rate via CoinGlass API publique (sans clé).
        Fallback : retourne 0.0 (neutre).
        """
        try:
            # CoinGlass endpoint public
            fsym = symbol.replace("USDT", "")
            resp = await self._client.get(
                "https://open-api.coinglass.com/public/v2/funding",
                params={"symbol": fsym},
            )
            resp.raise_for_status()
            data = resp.json()
            # Cherche Binance dans la liste
            for item in data.get("data", []):
                if item.get("exchangeName") in ("Binance", "Bybit"):
                    return float(item.get("rate", 0)) * 100
        except Exception as e:
            logger.debug(f"funding_rate_failed symbol={symbol}: {e}")
        return 0.0

    async def get_open_interest(self, symbol: str) -> float | None:
        return None

    async def health_check(self) -> bool:
        """Health check via CryptoCompare — toujours accessible."""
        try:
            resp = await self._client.get(
                f"{CRYPTOCOMPARE_BASE}/data/v2/histohour",
                params={"fsym": "BTC", "tsym": "USDT", "limit": 1},
            )
            data = resp.json()
            return data.get("Response") == "Success"
        except Exception:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()