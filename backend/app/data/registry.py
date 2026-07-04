"""
Registre multi-marchés — fait correspondre chaque symbole/marché au bon
MarketDataProvider, pour que le Scanner puisse traiter crypto, forex et
actions sans logique conditionnelle dispersée dans tout le code.

Usage typique :
    registry = MarketRegistry()
    registry.register("crypto", BinanceProvider())
    registry.register("forex", TwelveDataProvider())
    registry.register("stocks", TwelveDataProvider())

    provider = registry.get_provider_for("crypto")
"""

from dataclasses import dataclass

from app.data.base import MarketDataProvider


@dataclass
class MarketAsset:
    """Un actif à scanner, avec le marché auquel il appartient."""
    symbol: str
    market: str  # "crypto" | "forex" | "stocks"
    timeframe: str


class MarketRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, MarketDataProvider] = {}

    def register(self, market: str, provider: MarketDataProvider) -> None:
        self._providers[market] = provider

    def get_provider_for(self, market: str) -> MarketDataProvider:
        provider = self._providers.get(market)
        if provider is None:
            raise ValueError(
                f"Aucun provider enregistré pour le marché '{market}'. "
                f"Marchés disponibles : {list(self._providers.keys())}"
            )
        return provider

    def all_providers(self) -> list[MarketDataProvider]:
        return list(self._providers.values())

    async def health_check_all(self) -> dict[str, bool]:
        results = {}
        for market, provider in self._providers.items():
            try:
                results[market] = await provider.health_check()
            except Exception:
                results[market] = False
        return results

    async def aclose_all(self) -> None:
        for provider in self._providers.values():
            aclose = getattr(provider, "aclose", None)
            if aclose is not None:
                await aclose()


def build_default_registry() -> MarketRegistry:
    """
    Construit le registre par défaut : Binance pour la crypto, Twelve Data
    pour forex et actions (si une clé API est configurée — sinon ces deux
    marchés restent simplement indisponibles, sans casser le reste du
    système).
    """
    from app.config import settings
    from app.data.binance_provider import BinanceProvider

    registry = MarketRegistry()
    registry.register("crypto", BinanceProvider())

    if settings.twelvedata_api_key:
        from app.data.twelvedata_provider import TwelveDataProvider

        td_provider = TwelveDataProvider()
        registry.register("forex", td_provider)
        registry.register("stocks", td_provider)

    return registry


def default_multi_market_targets() -> list[MarketAsset]:
    """
    Liste d'actifs multi-marchés par défaut. Les marchés forex/stocks ne
    seront effectivement scannés que si une clé Twelve Data est configurée
    (sinon ils sont ignorés proprement par le scheduler, voir
    app/core/scheduler.py).
    """
    return [
        MarketAsset(symbol="BTCUSDT", market="crypto", timeframe="15m"),
        MarketAsset(symbol="ETHUSDT", market="crypto", timeframe="15m"),
        MarketAsset(symbol="EUR/USD", market="forex", timeframe="15m"),
        MarketAsset(symbol="AAPL", market="stocks", timeframe="15m"),
    ]
