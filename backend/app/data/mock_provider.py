"""
Fournisseur de données simulé — utile pour les tests locaux et pour
valider le pipeline complet sans dépendre d'un accès réseau externe.

NE PAS utiliser en production : c'est un générateur de prix aléatoires,
pas une vraie source de marché.
"""

from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

from app.data.base import MarketDataProvider


class MockProvider(MarketDataProvider):
    name = "mock"

    def __init__(self, seed: int = 123, trend_per_candle: float = 0.3):
        self.seed = seed
        self.trend_per_candle = trend_per_candle

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        closes = 100.0 + np.arange(limit) * self.trend_per_candle + rng.normal(0, 0.5, limit)
        now = datetime.now(timezone.utc)
        timestamps = [now - timedelta(minutes=15 * (limit - i)) for i in range(limit)]

        df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": closes - 0.1,
                "high": closes + rng.uniform(0.2, 0.8, limit),
                "low": closes - rng.uniform(0.2, 0.8, limit),
                "close": closes,
                "volume": rng.uniform(100, 500, limit),
            }
        )
        return df

    async def health_check(self) -> bool:
        return True

    async def aclose(self) -> None:
        pass
