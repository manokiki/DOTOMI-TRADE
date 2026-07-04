"""
Tests unitaires du Scheduler — section 6 et 11.5 du prompt maître.

On vérifie : la boucle persiste les setups en continu, un symbole en panne
n'arrête pas les autres, l'alerte de panne système se déclenche une seule
fois après le seuil d'échecs, et le routage multi-marchés ignore proprement
un marché sans provider enregistré.
"""

import asyncio

import pytest
from sqlalchemy import select, func

import app.alerting.email_alerts as alerting
import app.core.scheduler as scheduler_module
from app.core.scheduler import run_scan_loop, ScanTarget, FAILURE_THRESHOLD_FOR_DOWN_ALERT
from app.data.base import MarketDataProvider
from app.data.mock_provider import MockProvider
from app.data.registry import MarketRegistry
from app.db.models import TradeSetup, SystemHealthLog
from app.db.session import init_db, AsyncSessionLocal


class AlwaysFailProvider(MarketDataProvider):
    name = "always_fail"

    async def get_ohlcv(self, symbol, timeframe, limit=200):
        raise ConnectionError("simulated network failure")

    async def health_check(self):
        return False


@pytest.fixture(autouse=True)
async def fresh_db():
    """Garantit que les tables existent avant chaque test (idempotent)."""
    await init_db()
    yield


@pytest.mark.asyncio
async def test_scan_loop_persists_setups_for_each_symbol():
    stop_event = asyncio.Event()
    provider = MockProvider(seed=1, trend_per_candle=0.2)
    targets = [
        ScanTarget(symbol="MOCKA", timeframe="15m", interval_seconds=0.2),
        ScanTarget(symbol="MOCKB", timeframe="15m", interval_seconds=0.2),
    ]

    async def stopper():
        await asyncio.sleep(1.0)
        stop_event.set()

    await asyncio.gather(run_scan_loop(provider, targets, stop_event=stop_event), stopper())

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(TradeSetup))).scalars().all()
        symbols_seen = {r.symbol for r in rows}

    assert "MOCKA" in symbols_seen
    assert "MOCKB" in symbols_seen


@pytest.mark.asyncio
async def test_failing_symbol_does_not_block_healthy_symbol():
    stop_event = asyncio.Event()
    registry = MarketRegistry()
    registry.register("crypto", MockProvider(seed=2, trend_per_candle=0.1))
    registry.register("broken", AlwaysFailProvider())

    targets = [
        ScanTarget(symbol="HEALTHY", timeframe="15m", interval_seconds=0.2, market="crypto"),
        ScanTarget(symbol="BROKEN", timeframe="15m", interval_seconds=0.2, market="broken"),
    ]

    async def stopper():
        await asyncio.sleep(1.0)
        stop_event.set()

    await asyncio.gather(run_scan_loop(registry, targets, stop_event=stop_event), stopper())

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(TradeSetup))).scalars().all()
        symbols_seen = {r.symbol for r in rows}

    # Le symbole sain a bien continué à produire des setups malgré l'échec du voisin.
    assert "HEALTHY" in symbols_seen
    assert "BROKEN" not in symbols_seen


@pytest.mark.asyncio
async def test_down_alert_fires_once_after_threshold(monkeypatch):
    alerts_sent = []

    async def fake_alert(component, error_message):
        alerts_sent.append(component)
        return True

    monkeypatch.setattr(scheduler_module, "send_system_down_alert", fake_alert)

    stop_event = asyncio.Event()
    provider = AlwaysFailProvider()
    targets = [ScanTarget(symbol="FAILSYM", timeframe="15m", interval_seconds=0.1)]

    async def stopper():
        await asyncio.sleep(1.0)
        stop_event.set()

    await asyncio.gather(run_scan_loop(provider, targets, stop_event=stop_event), stopper())

    # Au moins le seuil d'échecs a été dépassé, et l'alerte n'a été envoyée
    # qu'une seule fois malgré de nombreux cycles d'échec supplémentaires.
    assert len(alerts_sent) == 1
    assert "FAILSYM" in alerts_sent[0]


@pytest.mark.asyncio
async def test_unregistered_market_is_skipped_without_crashing():
    stop_event = asyncio.Event()
    registry = MarketRegistry()
    registry.register("crypto", MockProvider(seed=3))
    # Aucun provider pour "stocks" : volontaire.

    targets = [
        ScanTarget(symbol="BTCUSDT", timeframe="15m", interval_seconds=0.2, market="crypto"),
        ScanTarget(symbol="AAPL", timeframe="15m", interval_seconds=0.2, market="stocks"),
    ]

    async def stopper():
        await asyncio.sleep(0.6)
        stop_event.set()

    # Ne doit lever aucune exception.
    await asyncio.gather(run_scan_loop(registry, targets, stop_event=stop_event), stopper())
