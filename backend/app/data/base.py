"""
Interface abstraite que tout fournisseur de données de marché doit respecter.

Le Scanner ne parle jamais directement à Binance, OANDA ou Polygon.io : il
parle à cette interface. Ça permet d'ajouter ou de remplacer une source de
données sans toucher au reste du système (Scanner, Score Engine, etc.) —
voir section 3 du prompt maître.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd


@dataclass
class Candle:
    """Une bougie OHLCV unique, normalisée quel que soit le fournisseur d'origine."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(ABC):
    """Interface que chaque connecteur de marché (Binance, OANDA, ...) doit implémenter."""

    name: str = "unknown"

    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """
        Retourne un DataFrame avec les colonnes :
        timestamp (datetime, UTC), open, high, low, close, volume.
        Trié par timestamp croissant. La dernière ligne est la bougie la plus récente.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Retourne True si la source de données répond correctement."""
        raise NotImplementedError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
