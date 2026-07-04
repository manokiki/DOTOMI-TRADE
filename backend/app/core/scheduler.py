"""
Scheduler — fait tourner le Scanner en continu, sans intervention humaine,
sur tous les symboles configurés, à travers un ou plusieurs marchés
(crypto, forex, actions) via le MarketRegistry (section 3 et 11.5 du
prompt maître : extension multi-marchés).

C'est le composant qui transforme DOTOMI-TRADE d'un système "à la demande"
(appelé via /scanner) en un système réellement 24h/24 : une boucle de fond
qui scanne chaque symbole à intervalle régulier, journalise sa propre santé,
et alerte en cas de panne (section 6 du prompt maître).

Conçu pour tourner soit comme process autonome (`python -m app.core.scheduler`),
soit lancé en tâche de fond par l'API au démarrage (voir app/api/main.py).
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.alerting.email_alerts import send_system_down_alert
from app.config import settings
from app.core.scanner import scan_symbol, record_health
from app.data.base import MarketDataProvider
from app.data.registry import MarketRegistry, build_default_registry, default_multi_market_targets
from app.db.session import AsyncSessionLocal, init_db
from app.risk.risk_center import DailyRiskState

logger = logging.getLogger("dotomi.scheduler")


@dataclass
class ScanTarget:
    """Un actif à scanner en continu, avec son propre intervalle et son marché d'origine."""
    symbol: str
    timeframe: str
    interval_seconds: int
    market: str = "crypto"


class SchedulerState:
    """
    Suivi de l'état du scheduler lui-même : combien d'échecs consécutifs par
    symbole, pour déclencher l'alerte de panne système une seule fois plutôt
    qu'à chaque cycle (éviter le spam d'emails).
    """

    def __init__(self) -> None:
        self.consecutive_failures: dict[str, int] = {}
        self.last_success: dict[str, datetime] = {}
        self.down_alert_sent: dict[str, bool] = {}

    def record_success(self, symbol: str) -> None:
        self.consecutive_failures[symbol] = 0
        self.last_success[symbol] = datetime.now(timezone.utc)
        self.down_alert_sent[symbol] = False

    def record_failure(self, symbol: str) -> int:
        self.consecutive_failures[symbol] = self.consecutive_failures.get(symbol, 0) + 1
        return self.consecutive_failures[symbol]


# Seuil au-delà duquel on considère qu'un symbole est réellement "en panne"
# (pas juste un hoquet réseau ponctuel déjà géré par le retry du provider).
FAILURE_THRESHOLD_FOR_DOWN_ALERT = 3


async def run_scan_loop(
    provider: MarketDataProvider | MarketRegistry,
    targets: list[ScanTarget],
    user_id: int = 1,
    capital: float | None = None,
    stop_event: asyncio.Event | None = None,
) -> None:
    """
    Boucle principale : lance une tâche asyncio indépendante par symbole
    (chaque symbole a son propre intervalle et ses propres échecs, un
    symbole en panne ne doit jamais bloquer le scan des autres).

    `provider` peut être soit un MarketDataProvider unique (compatibilité
    V1 mono-marché), soit un MarketRegistry pour router chaque cible vers
    le provider de son marché. Un symbole dont le marché n'a pas de
    provider enregistré est simplement ignoré (averti une fois), plutôt que
    de faire planter toute la boucle.
    """
    capital = capital if capital is not None else settings.default_capital
    state = SchedulerState()

    tasks = []
    for target in targets:
        try:
            resolved_provider = (
                provider.get_provider_for(target.market) if isinstance(provider, MarketRegistry) else provider
            )
        except ValueError as exc:
            logger.warning("scan_target_skipped_no_provider", extra={"symbol": target.symbol, "error": str(exc)})
            continue
        tasks.append(
            asyncio.create_task(
                _scan_one_symbol_forever(resolved_provider, target, user_id, capital, state, stop_event)
            )
        )

    if not tasks:
        logger.error("scan_loop_no_valid_targets")
        return

    await asyncio.gather(*tasks)


async def _scan_one_symbol_forever(
    provider: MarketDataProvider,
    target: ScanTarget,
    user_id: int,
    capital: float,
    state: SchedulerState,
    stop_event: asyncio.Event | None,
) -> None:
    while True:
        if stop_event is not None and stop_event.is_set():
            logger.info("scan_loop_stopped", extra={"symbol": target.symbol})
            return

        cycle_start = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            try:
                risk_state = await _build_risk_state(db, user_id, capital, target.symbol)
                result = await scan_symbol(
                    provider, target.symbol, target.timeframe, user_id, capital, risk_state, db=db
                )
                state.record_success(target.symbol)
                latency_ms = (datetime.now(timezone.utc) - cycle_start).total_seconds() * 1000
                await record_health(db, component=f"scanner:{target.symbol}", status="OK", latency_ms=latency_ms)
                logger.info(
                    "scheduled_scan_ok",
                    extra={"symbol": target.symbol, "status": result.status, "score": result.total_score},
                )
            except Exception as exc:  # noqa: BLE001 — une panne d'un symbole ne doit jamais tuer la boucle
                failures = state.record_failure(target.symbol)
                logger.error(
                    "scheduled_scan_failed",
                    extra={"symbol": target.symbol, "consecutive_failures": failures, "error": str(exc)},
                )
                try:
                    await record_health(
                        db, component=f"scanner:{target.symbol}", status="DOWN", error=str(exc)
                    )
                except Exception:
                    logger.error("health_log_write_failed", extra={"symbol": target.symbol})

                if failures >= FAILURE_THRESHOLD_FOR_DOWN_ALERT and not state.down_alert_sent.get(target.symbol):
                    sent = await send_system_down_alert(
                        component=f"Scanner — {target.symbol}",
                        error_message=(
                            f"{failures} échecs consécutifs lors du scan de {target.symbol}. "
                            f"Dernière erreur : {exc}"
                        ),
                    )
                    state.down_alert_sent[target.symbol] = sent

        await asyncio.sleep(target.interval_seconds)


async def _build_risk_state(db, user_id: int, capital: float, symbol: str) -> DailyRiskState:
    """
    Construit l'état de risque journalier réel à partir des trades déjà
    journalisés aujourd'hui — jamais un état inventé. En V1 mono-utilisateur,
    on requête simplement les trades du jour pour cet utilisateur.
    """
    from datetime import timedelta

    from sqlalchemy import select

    from app.db.models import Trade

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    stmt = select(Trade).where(Trade.user_id == user_id, Trade.opened_at >= week_start)
    trades = (await db.execute(stmt)).scalars().all()

    daily_pnl = sum(t.pnl or 0.0 for t in trades if t.opened_at and t.opened_at >= today_start)
    weekly_pnl = sum(t.pnl or 0.0 for t in trades)
    trades_today = len([t for t in trades if t.opened_at and t.opened_at >= today_start])

    return DailyRiskState(
        capital=capital, daily_pnl=daily_pnl, weekly_pnl=weekly_pnl, trades_taken_today=trades_today
    )


def default_targets() -> list[ScanTarget]:
    """
    Liste de symboles à scanner par défaut, multi-marchés. Les marchés
    forex/stocks ne seront effectivement scannés que si une clé Twelve Data
    est configurée (sinon ignorés proprement, voir run_scan_loop).
    """
    multi = default_multi_market_targets()
    return [
        ScanTarget(symbol=a.symbol, timeframe=a.timeframe, interval_seconds=60, market=a.market)
        for a in multi
    ]


async def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    await init_db()
    registry = build_default_registry()
    try:
        await run_scan_loop(registry, default_targets())
    finally:
        await registry.aclose_all()


if __name__ == "__main__":
    asyncio.run(_main())
