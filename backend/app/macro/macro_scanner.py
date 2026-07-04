"""
Macro Scanner — Version finale avec toutes les sources.

Sources actives :
- alternative.me  : Fear & Greed Index (sans clé)
- Binance Futures : funding rate BTC/ETH (sans clé, public)
- Bybit API       : funding rate cross-vérif (clé optionnelle)
- Twelve Data     : DXY, VIX, S&P500 (clé gratuite)
- FRED API        : CPI trend, M2, taux Fed (clé gratuite)
- RSS feeds       : news sentiment (sans clé, feedparser)
- yfinance        : fallback DXY/VIX si Twelve Data échoue (sans clé)

Installation : pip install yfinance feedparser
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger("dotomi.macro")


# ── Contexte ──────────────────────────────────────────────────────────────────

class MacroContext:
    FAVORABLE = "FAVORABLE"
    NEUTRAL   = "NEUTRAL"
    HOSTILE   = "HOSTILE"
    CRISIS    = "CRISIS"


@dataclass
class FearGreedData:
    value: int = 50
    classification: str = "Neutral"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OnChainData:
    funding_rate_btc: float = 0.0
    funding_rate_eth: float = 0.0
    open_interest_btc: float = 0.0
    open_interest_eth: float = 0.0


@dataclass
class MacroData:
    fear_greed: FearGreedData = field(default_factory=FearGreedData)
    dxy: float | None = None
    vix: float | None = None
    sp500_change_pct: float | None = None
    cpi_trend: str | None = None        # "rising" | "falling" | "stable"
    m2_trend: str | None = None         # "expanding" | "contracting"
    fed_rate: float | None = None
    onchain: OnChainData = field(default_factory=OnChainData)
    news_sentiment: float = 0.5
    has_high_impact_event_soon: bool = False
    next_event_name: str | None = None
    next_event_hours: float | None = None
    context: str = MacroContext.NEUTRAL
    macro_score: float = 2.5


# ── Mots-clés sentiment ───────────────────────────────────────────────────────

POSITIVE = {
    "surge", "soar", "rally", "bullish", "breakout", "adoption", "approve",
    "approved", "etf", "launch", "partnership", "upgrade", "record", "high",
    "gain", "rise", "grow", "strong", "institutional", "buy", "accumulate",
    "support", "milestone", "breakthrough", "mainstream", "positive",
    "hausse", "montée", "croissance", "approbation",
}

NEGATIVE = {
    "crash", "collapse", "ban", "hack", "fraud", "scam", "bearish", "dump",
    "sell", "fear", "panic", "lawsuit", "investigation", "fine", "sanction",
    "restrict", "decline", "fall", "drop", "plunge", "lose", "lost", "theft",
    "regulation", "crackdown", "warning", "risk", "concern", "worry",
    "chute", "effondrement", "interdiction", "fraude", "baisse",
}


# ── MacroScanner ──────────────────────────────────────────────────────────────

class MacroScanner:

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=8.0,
            headers={"User-Agent": "Mozilla/5.0 DOTOMI-TRADE/2.0"},
        )
        self._cache: dict = {}
        self._cache_ts: dict = {}

    async def get_full_macro(self) -> MacroData:
        import asyncio
        results = await asyncio.gather(
            self._fetch_fear_greed(),
            self._fetch_market_data_twelvedata(),
            self._fetch_fred_data(),
            self._fetch_funding_binance(),
            self._fetch_news_rss(),
            return_exceptions=True,
        )

        data = MacroData()

        if isinstance(results[0], FearGreedData):
            data.fear_greed = results[0]

        if isinstance(results[1], dict):
            data.dxy             = results[1].get("dxy")
            data.vix             = results[1].get("vix")
            data.sp500_change_pct = results[1].get("sp500_change_pct")

        # Si Twelve Data a échoué, fallback yfinance
        if data.dxy is None and data.vix is None:
            yf_data = await self._fetch_market_data_yfinance()
            data.dxy             = yf_data.get("dxy")
            data.vix             = yf_data.get("vix")
            data.sp500_change_pct = yf_data.get("sp500_change_pct")

        if isinstance(results[2], dict):
            data.cpi_trend = results[2].get("cpi_trend")
            data.m2_trend  = results[2].get("m2_trend")
            data.fed_rate  = results[2].get("fed_rate")

        if isinstance(results[3], OnChainData):
            data.onchain = results[3]

        if isinstance(results[4], float):
            data.news_sentiment = results[4]

        data.context     = self._compute_context(data)
        data.macro_score = self._compute_score(data)

        logger.info(
            f"macro_ok context={data.context} score={data.macro_score:.1f} "
            f"fg={data.fear_greed.value} vix={data.vix} dxy={data.dxy} "
            f"funding_btc={data.onchain.funding_rate_btc:.4f}%"
        )
        return data

    # ── Fear & Greed ──────────────────────────────────────────────────────────

    async def _fetch_fear_greed(self) -> FearGreedData:
        if self._is_cached("fg", 3600):
            return self._cache["fg"]
        try:
            r = await self._client.get("https://api.alternative.me/fng/?limit=1")
            r.raise_for_status()
            d = r.json()["data"][0]
            result = FearGreedData(
                value=int(d["value"]),
                classification=d["value_classification"],
            )
            self._set("fg", result)
            return result
        except Exception as e:
            logger.warning(f"fear_greed_failed: {e}")
            return FearGreedData()

    # ── Twelve Data — DXY, VIX, S&P500 ───────────────────────────────────────

    async def _fetch_market_data_twelvedata(self) -> dict:
        """
        Twelve Data gratuit — 800 appels/jour.
        Tickers : DXY, VIX, SPX
        """
        if self._is_cached("market_td", 300):
            return self._cache["market_td"]

        if not settings.twelvedata_api_key:
            return {}

        try:
            r = await self._client.get(
                "https://api.twelvedata.com/quote",
                params={
                    "symbol": "DXY,VIX,SPX",
                    "apikey": settings.twelvedata_api_key,
                },
            )
            r.raise_for_status()
            raw = r.json()
            result = {}

            if "DXY" in raw and "close" in raw["DXY"]:
                result["dxy"] = float(raw["DXY"]["close"])

            if "VIX" in raw and "close" in raw["VIX"]:
                result["vix"] = float(raw["VIX"]["close"])

            if "SPX" in raw and "percent_change" in raw["SPX"]:
                result["sp500_change_pct"] = float(raw["SPX"]["percent_change"])

            self._set("market_td", result)
            return result

        except Exception as e:
            logger.warning(f"twelvedata_failed: {e}")
            return {}

    # ── yfinance — fallback DXY, VIX, S&P500 ─────────────────────────────────

    async def _fetch_market_data_yfinance(self) -> dict:
        """Fallback gratuit si Twelve Data échoue ou clé absente."""
        if self._is_cached("market_yf", 300):
            return self._cache["market_yf"]

        import asyncio
        result = await asyncio.get_event_loop().run_in_executor(
            None, self._yfinance_sync
        )
        if result:
            self._set("market_yf", result)
        return result

    def _yfinance_sync(self) -> dict:
        try:
            import yfinance as yf
            tickers = yf.download(
                ["DX-Y.NYB", "^VIX", "^GSPC"],
                period="5d", interval="1d",
                progress=False, auto_adjust=True,
            )
            if tickers.empty:
                return {}

            close  = tickers["Close"]
            result = {}

            dxy = close["DX-Y.NYB"].dropna()
            vix = close["^VIX"].dropna()
            spx = close["^GSPC"].dropna()

            if not dxy.empty: result["dxy"] = round(float(dxy.iloc[-1]), 3)
            if not vix.empty: result["vix"] = round(float(vix.iloc[-1]), 2)
            if len(spx) >= 2:
                chg = (float(spx.iloc[-1]) - float(spx.iloc[-2])) / float(spx.iloc[-2]) * 100
                result["sp500_change_pct"] = round(chg, 3)

            return result
        except ImportError:
            logger.warning("yfinance non installé — pip install yfinance")
            return {}
        except Exception as e:
            logger.warning(f"yfinance_failed: {e}")
            return {}

    # ── FRED API — CPI, M2, taux Fed ─────────────────────────────────────────

    async def _fetch_fred_data(self) -> dict:
        """
        FRED API gratuit — fred.stlouisfed.org
        Séries : FEDFUNDS (taux Fed), CPIAUCSL (CPI), M2SL (M2)
        """
        if self._is_cached("fred", 86400):  # cache 24h — données mensuelles
            return self._cache["fred"]

        if not settings.fred_api_key:
            return {}

        import asyncio
        results = await asyncio.gather(
            self._fred_series("FEDFUNDS", 3),
            self._fred_series("CPIAUCSL", 4),
            self._fred_series("M2SL", 4),
            return_exceptions=True,
        )

        data = {}

        # Taux Fed
        if isinstance(results[0], list) and results[0]:
            data["fed_rate"] = float(results[0][-1]["value"])

        # CPI trend (comparaison 3 dernières valeurs)
        if isinstance(results[1], list) and len(results[1]) >= 3:
            vals = [float(r["value"]) for r in results[1] if r["value"] != "."]
            if len(vals) >= 3:
                if vals[-1] > vals[-2] > vals[-3]:
                    data["cpi_trend"] = "rising"
                elif vals[-1] < vals[-2] < vals[-3]:
                    data["cpi_trend"] = "falling"
                else:
                    data["cpi_trend"] = "stable"

        # M2 trend
        if isinstance(results[2], list) and len(results[2]) >= 3:
            vals = [float(r["value"]) for r in results[2] if r["value"] != "."]
            if len(vals) >= 3:
                data["m2_trend"] = "expanding" if vals[-1] > vals[-3] else "contracting"

        self._set("fred", data)
        return data

    async def _fred_series(self, series_id: str, limit: int = 4) -> list:
        """Récupère les dernières valeurs d'une série FRED."""
        try:
            r = await self._client.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id":    series_id,
                    "api_key":      settings.fred_api_key,
                    "file_type":    "json",
                    "sort_order":   "desc",
                    "limit":        limit,
                },
            )
            r.raise_for_status()
            obs = r.json().get("observations", [])
            return list(reversed(obs))
        except Exception as e:
            logger.warning(f"fred_series_failed series={series_id}: {e}")
            return []

    # ── Funding rate Binance (sans clé) ───────────────────────────────────────

    async def _fetch_funding_binance(self) -> OnChainData:
        if self._is_cached("funding", 1800):
            return self._cache["funding"]

        data = OnChainData()
        try:
            import asyncio
            r_btc, r_eth = await asyncio.gather(
                self._client.get(
                    "https://fapi.binance.com/fapi/v1/premiumIndex",
                    params={"symbol": "BTCUSDT"},
                ),
                self._client.get(
                    "https://fapi.binance.com/fapi/v1/premiumIndex",
                    params={"symbol": "ETHUSDT"},
                ),
                return_exceptions=True,
            )
            if not isinstance(r_btc, Exception):
                r_btc.raise_for_status()
                data.funding_rate_btc = float(
                    r_btc.json().get("lastFundingRate", 0)
                ) * 100
            if not isinstance(r_eth, Exception):
                r_eth.raise_for_status()
                data.funding_rate_eth = float(
                    r_eth.json().get("lastFundingRate", 0)
                ) * 100
            self._set("funding", data)

        except Exception as e:
            logger.warning(f"binance_funding_failed — fallback Bybit: {e}")
            data = await self._fetch_funding_bybit()

        return data

    async def _fetch_funding_bybit(self) -> OnChainData:
        """Bybit public — fallback ou cross-vérification."""
        data = OnChainData()
        try:
            import asyncio
            r_btc, r_eth = await asyncio.gather(
                self._client.get(
                    "https://api.bybit.com/v5/market/tickers",
                    params={"category": "linear", "symbol": "BTCUSDT"},
                ),
                self._client.get(
                    "https://api.bybit.com/v5/market/tickers",
                    params={"category": "linear", "symbol": "ETHUSDT"},
                ),
                return_exceptions=True,
            )
            if not isinstance(r_btc, Exception):
                r_btc.raise_for_status()
                lst = r_btc.json().get("result", {}).get("list", [])
                if lst:
                    data.funding_rate_btc = float(lst[0].get("fundingRate", 0)) * 100
            if not isinstance(r_eth, Exception):
                r_eth.raise_for_status()
                lst = r_eth.json().get("result", {}).get("list", [])
                if lst:
                    data.funding_rate_eth = float(lst[0].get("fundingRate", 0)) * 100
        except Exception as e:
            logger.warning(f"bybit_funding_failed: {e}")
        return data

    # ── News sentiment via RSS (sans clé) ─────────────────────────────────────

    async def _fetch_news_rss(self) -> float:
        if self._is_cached("news", 600):
            return self._cache["news"]

        feeds = [
            "https://feeds.feedburner.com/CoinDesk",
            "https://cointelegraph.com/rss",
            "https://decrypt.co/feed",
            "https://bitcoinmagazine.com/.rss/full/",
            "https://cryptonews.com/news/feed/",
        ]

        import asyncio
        results = await asyncio.gather(
            *[self._parse_rss(url) for url in feeds],
            return_exceptions=True,
        )

        titles = []
        for r in results:
            if isinstance(r, list):
                titles.extend(r)

        if not titles:
            return 0.5

        sentiment = self._sentiment_score(titles)
        self._set("news", sentiment)
        logger.info(f"news_sentiment={sentiment:.2f} articles={len(titles)}")
        return sentiment

    async def _parse_rss(self, url: str) -> list[str]:
        try:
            r = await self._client.get(url, follow_redirects=True)
            r.raise_for_status()
            try:
                import feedparser
                feed = feedparser.parse(r.text)
                return [e.title for e in feed.entries[:15] if hasattr(e, "title")]
            except ImportError:
                titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", r.text)
                if not titles:
                    titles = re.findall(r"<title>(.*?)</title>", r.text)
                return [t.strip() for t in titles[1:16]]
        except Exception as e:
            logger.debug(f"rss_failed url={url}: {e}")
            return []

    def _sentiment_score(self, titles: list[str]) -> float:
        scores = []
        for title in titles:
            words = set(re.findall(r"\b\w+\b", title.lower()))
            pos = len(words & POSITIVE)
            neg = len(words & NEGATIVE)
            if pos + neg == 0:
                scores.append(0.5)
            else:
                scores.append(pos / (pos + neg))
        return round(sum(scores) / len(scores), 3) if scores else 0.5

    # ── Contexte global ───────────────────────────────────────────────────────

    def _compute_context(self, d: MacroData) -> str:
        fg  = d.fear_greed.value
        vix = d.vix
        dxy = d.dxy
        fr  = d.onchain.funding_rate_btc
        sp  = d.sp500_change_pct
        cpi = d.cpi_trend
        m2  = d.m2_trend

        # CRISIS
        if (vix and vix > settings.vix_crisis_threshold) or fg < 10:
            return MacroContext.CRISIS

        # HOSTILE
        hostile = 0
        if dxy and dxy > settings.dxy_hostile_threshold:             hostile += 2
        if vix and vix > settings.vix_hostile_threshold:             hostile += 2
        if sp and sp < -2.0:                                          hostile += 1
        if fr > settings.funding_rate_hot:                            hostile += 1
        if fg < settings.fear_greed_extreme_fear:                     hostile += 1
        if cpi == "rising":                                           hostile += 1
        if m2 == "contracting":                                       hostile += 1
        if d.has_high_impact_event_soon and (d.next_event_hours or 99) < 2:
            hostile += 2
        if hostile >= 3:
            return MacroContext.HOSTILE

        # FAVORABLE
        favorable = 0
        if dxy and dxy < settings.dxy_favorable_threshold:            favorable += 2
        if vix and vix < settings.vix_neutral_threshold:              favorable += 1
        if sp and sp > 0:                                              favorable += 1
        if -0.01 <= fr <= 0.01:                                       favorable += 1
        if settings.fear_greed_extreme_fear < fg < settings.fear_greed_extreme_greed:
            favorable += 1
        if d.news_sentiment > 0.6:                                    favorable += 1
        if cpi == "falling":                                           favorable += 1
        if m2 == "expanding":                                          favorable += 1
        if favorable >= 3:
            return MacroContext.FAVORABLE

        return MacroContext.NEUTRAL

    def _compute_score(self, d: MacroData) -> float:
        """Score 0.0 à 5.0 pour le Scoring Engine."""
        ctx = d.context
        if ctx == MacroContext.CRISIS:   return 0.0
        if ctx == MacroContext.HOSTILE:  return 1.0
        if ctx == MacroContext.NEUTRAL:  return 2.5

        # FAVORABLE — score précis
        score = 3.0
        if d.dxy and d.dxy < 101:             score += 0.5
        if d.vix and d.vix < 18:              score += 0.5
        if d.fear_greed.value > 50:           score += 0.5
        if d.news_sentiment > 0.65:           score += 0.5
        if d.cpi_trend == "falling":          score += 0.3
        if d.m2_trend == "expanding":         score += 0.2
        return min(5.0, score)

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _is_cached(self, key: str, ttl: int) -> bool:
        if key not in self._cache or key not in self._cache_ts:
            return False
        return (datetime.now(timezone.utc) - self._cache_ts[key]).total_seconds() < ttl

    def _set(self, key: str, value) -> None:
        self._cache[key]    = value
        self._cache_ts[key] = datetime.now(timezone.utc)

    async def aclose(self) -> None:
        await self._client.aclose()
