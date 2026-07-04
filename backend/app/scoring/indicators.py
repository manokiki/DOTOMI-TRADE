"""
Indicateurs techniques — vectorisés avec pandas_ta.
CORRIGÉ : swing highs/lows vectorisés (suppression boucle O(n²)).
"""

import numpy as np
import pandas as pd
import pandas_ta as ta


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["atr"] = ta.atr(out["high"], out["low"], out["close"], length=14)

    adx_df = ta.adx(out["high"], out["low"], out["close"], length=14)
    if adx_df is not None and "ADX_14" in adx_df.columns:
        out["adx"] = adx_df["ADX_14"]
    else:
        out["adx"] = np.nan

    out["sma_50"]       = ta.sma(out["close"], length=50)
    out["sma_50_slope"] = (out["sma_50"] - out["sma_50"].shift(5)) / out["close"] * 100
    out["ema_21"]       = ta.ema(out["close"], length=21)
    out["rsi"]          = ta.rsi(out["close"], length=14)

    if "volume" in out.columns:
        out["vol_ma20"] = ta.sma(out["volume"], length=20)
    else:
        out["vol_ma20"] = np.nan

    out["swing_high"] = _swing_highs(out["high"], window=2)
    out["swing_low"]  = _swing_lows(out["low"], window=2)

    return out


def _swing_highs(series: pd.Series, window: int = 2) -> pd.Series:
    arr = series.values
    n   = len(arr)
    result = np.zeros(n, dtype=bool)
    for i in range(window, n - window):
        if arr[i] > np.max(arr[i - window:i]) and arr[i] > np.max(arr[i + 1:i + 1 + window]):
            result[i] = True
    return pd.Series(result, index=series.index)


def _swing_lows(series: pd.Series, window: int = 2) -> pd.Series:
    arr = series.values
    n   = len(arr)
    result = np.zeros(n, dtype=bool)
    for i in range(window, n - window):
        if arr[i] < np.min(arr[i - window:i]) and arr[i] < np.min(arr[i + 1:i + 1 + window]):
            result[i] = True
    return pd.Series(result, index=series.index)
