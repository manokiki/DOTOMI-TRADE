"""
Script CLI pour lancer un backtest sur un historique réel récupéré depuis
Binance.

Usage :
    python scripts/run_backtest.py --symbol BTCUSDT --timeframe 15m --candles 1000

Note : l'API publique Binance limite chaque appel à 1000 bougies. Pour un
historique plus long (l'objectif final étant plusieurs années — section 8
du prompt maître), il faut paginer les appels en remontant dans le temps
avec le paramètre `endTime`. Ce script fait cette pagination automatiquement.
"""

import argparse
import asyncio
import logging

import pandas as pd

from app.core.backtest import run_backtest
from app.data.binance_provider import BinanceProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("dotomi.backtest_cli")


async def fetch_long_history(provider: BinanceProvider, symbol: str, timeframe: str, total_candles: int) -> pd.DataFrame:
    """
    Récupère un historique plus long que la limite de 1000 bougies par
    appel, en paginant vers le passé.
    """
    all_chunks = []
    remaining = total_candles
    end_time_param = {}

    while remaining > 0:
        batch_size = min(1000, remaining)
        params = {"symbol": symbol.upper(), "interval": timeframe, "limit": batch_size}
        params.update(end_time_param)

        raw = await provider._request_with_retry("/api/v3/klines", params=params)
        if not raw:
            break

        chunk_rows = [
            {
                "timestamp": pd.to_datetime(k[0], unit="ms", utc=True),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            }
            for k in raw
        ]
        all_chunks.append(pd.DataFrame(chunk_rows))

        oldest_open_time_ms = raw[0][0]
        end_time_param = {"endTime": oldest_open_time_ms - 1}
        remaining -= len(raw)

        if len(raw) < batch_size:
            break  # plus de données disponibles plus tôt dans l'historique

    full = pd.concat(all_chunks).drop_duplicates(subset="timestamp").sort_values("timestamp")
    return full.reset_index(drop=True)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest DOTOMI-TRADE sur historique Binance")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", default="15m")
    parser.add_argument("--candles", type=int, default=2000, help="Nombre total de bougies historiques à charger")
    args = parser.parse_args()

    provider = BinanceProvider()
    try:
        logger.info("fetching_history", extra={"symbol": args.symbol, "candles": args.candles})
        history = await fetch_long_history(provider, args.symbol, args.timeframe, args.candles)
        logger.info("history_fetched", extra={"rows": len(history)})

        results, stats = run_backtest(args.symbol, history)

        print("\n=== RÉSULTATS DU BACKTEST ===")
        print(f"Symbole              : {args.symbol}")
        print(f"Timeframe             : {args.timeframe}")
        print(f"Bougies analysées     : {len(history)}")
        print(f"Setups évalués        : {stats.total_setups_seen}")
        print(f"Setups autorisés      : {stats.total_authorized}")
        print(f"Trades simulés        : {stats.trades_simulated}")
        print(f"Taux de réussite      : {stats.win_rate_pct} %")
        print(f"R moyen par trade     : {stats.average_r_multiple}")
        print(f"Profit factor         : {stats.profit_factor}")
        print(f"Drawdown max (en R)   : {stats.max_drawdown_r}")
        print("\nRappel : ces chiffres décrivent UNIQUEMENT le passé observé sur cet")
        print("échantillon. Ils ne garantissent aucune performance future.")
    finally:
        await provider.aclose()


if __name__ == "__main__":
    asyncio.run(main())
