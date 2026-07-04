"""
Score Engine — 9 critères sur 100.

CORRECTIONS vs version originale :
1. score_timing() : kill zones exactes, hors zone = 0
2. score_risk()   : RRR < 2.5 → score 0 (rejet immédiat)
3. compute_score(): reçoit macro optionnel (critères macro + onchain)
4. ScoreResult    : nouveaux champs session_name, entry_window, macro_context
5. SubScores      : champs macro et onchain (default 0.0 si pas de macro)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.config import settings
from app.scoring.indicators import compute_indicators


@dataclass
class SubScores:
    regime:       float
    structure:    float
    liquidity:    float
    pullback:     float
    timing:       float
    confirmation: float
    risk:         float
    macro:        float = 0.0
    onchain:      float = 0.0
    reasons:      list[str] = field(default_factory=list)


@dataclass
class ScoreResult:
    symbol:              str
    direction:           str
    sub_scores:          SubScores
    total_score:         float
    status:              str
    entry_price:         float | None
    stop_loss:           float | None
    tp1:                 float | None
    tp2:                 float | None
    rrr:                 float | None
    reasons:             list[str]
    session_name:        str | None = None
    entry_window_start:  str | None = None
    entry_window_end:    str | None = None
    macro_context:       str = "NEUTRAL"


def _clip(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


# ── 1. Régime ─────────────────────────────────────────────────────────────────

def score_regime(df: pd.DataFrame) -> tuple[float, str | None]:
    last  = df.iloc[-1]
    adx   = last.get("adx", np.nan)
    slope = last.get("sma_50_slope", np.nan)

    if pd.isna(adx) or pd.isna(slope):
        return 0.0, None

    if adx < 15:                        # CHOP → rejet immédiat
        return 0.0, None
    if adx < 20:                        # Range
        return _clip(adx / 20 * 35), None

    bias      = "BUY" if slope > 0 else "SELL"
    intensity = _clip((adx - 20) / 45 * 100)
    return _clip(35 + intensity * 0.65), bias


# ── 2. Structure ──────────────────────────────────────────────────────────────

def score_structure(df: pd.DataFrame, bias: str | None) -> float:
    if bias is None:
        return 30.0
    w = df.tail(20)
    sh = w.loc[w["swing_high"], "high"]
    sl = w.loc[w["swing_low"],  "low"]
    if bias == "BUY":
        if len(sh) >= 2 and len(sl) >= 2:
            bos = sh.iloc[-1] > sh.iloc[-2]
            hl  = sl.iloc[-1] > sl.iloc[-2]
            if bos and hl:  return 90.0
            if bos or hl:   return 65.0
    else:
        if len(sh) >= 2 and len(sl) >= 2:
            bos = sl.iloc[-1] < sl.iloc[-2]
            lh  = sh.iloc[-1] < sh.iloc[-2]
            if bos and lh:  return 90.0
            if bos or lh:   return 65.0
    return 35.0


# ── 3. Liquidité ──────────────────────────────────────────────────────────────

def score_liquidity(df: pd.DataFrame, bias: str | None) -> float:
    if bias is None or len(df) < 10:
        return 30.0
    last   = df.iloc[-1]
    window = df.iloc[-10:-1]
    score  = 30.0

    if bias == "BUY":
        prior_low = window["low"].min()
        if last["low"] < prior_low and last["close"] > prior_low:
            score = 90.0
        elif _has_fvg(df, "BUY"):
            score = 70.0
    else:
        prior_high = window["high"].max()
        if last["high"] > prior_high and last["close"] < prior_high:
            score = 90.0
        elif _has_fvg(df, "SELL"):
            score = 70.0

    if _has_order_block(df, bias):
        score = min(100.0, score + 8.0)

    return _clip(score)


def _has_fvg(df: pd.DataFrame, bias: str) -> bool:
    for i in range(len(df) - 3, max(0, len(df) - 13), -1):
        c1, c3 = df.iloc[i], df.iloc[i + 2]
        if bias == "BUY"  and c3["low"]  > c1["high"]: return True
        if bias == "SELL" and c3["high"] < c1["low"]:  return True
    return False


def _has_order_block(df: pd.DataFrame, bias: str) -> bool:
    w = df.tail(10)
    for i in range(len(w) - 2, 0, -1):
        c, n = w.iloc[i], w.iloc[i + 1]
        if bias == "BUY":
            if c["close"] < c["open"]:
                if n["close"] > n["open"] and (n["close"] - n["open"]) > 2 * (c["open"] - c["close"]):
                    return True
        else:
            if c["close"] > c["open"]:
                if n["close"] < n["open"] and (n["open"] - n["close"]) > 2 * (c["close"] - c["open"]):
                    return True
    return False


# ── 4. Pullback ───────────────────────────────────────────────────────────────

def score_pullback(df: pd.DataFrame, bias: str | None) -> float:
    if bias is None or len(df) < 20:
        return 30.0
    w     = df.tail(20)
    close = float(df.iloc[-1]["close"])
    hi    = float(w["high"].max())
    lo    = float(w["low"].min())
    rng   = hi - lo
    if rng <= 0:
        return 30.0

    retrace = (hi - close) / rng if bias == "BUY" else (close - lo) / rng

    if 0.618 <= retrace <= 0.786:  return 100.0   # OTE zone
    if 0.382 <= retrace <  0.618:  return 85.0    # Fibonacci classique
    if 0.20  <= retrace <  0.382:  return 55.0
    return 25.0


# ── 5. Timing — CORRECTION CRITIQUE ──────────────────────────────────────────

def score_timing(df: pd.DataFrame) -> tuple[float, str | None, str | None, str | None]:
    """
    CORRIGÉ : hors kill zone = 0, trade bloqué automatiquement.
    Avant : score 35 même à 20h UTC un dimanche.
    """
    hour = int(df.iloc[-1]["timestamp"].hour)

    if settings.london_kz_start <= hour < settings.london_kz_end:
        return 100.0, "London Kill Zone", "07:00 UTC", "10:00 UTC"

    if settings.newyork_kz_start <= hour < settings.newyork_kz_end:
        return 100.0, "New York Kill Zone", "12:00 UTC", "15:00 UTC"

    if settings.ny_close_start <= hour < settings.ny_close_end:
        return 60.0, "NY Close", "17:00 UTC", "19:00 UTC"

    return 0.0, None, None, None


# ── 6. Confirmation ───────────────────────────────────────────────────────────

def score_confirmation(df: pd.DataFrame, bias: str | None) -> float:
    if bias is None:
        return 30.0
    last  = df.iloc[-1]
    rsi   = last.get("rsi", np.nan)
    score = 0.0

    closed_ok = last["close"] > last["open"] if bias == "BUY" else last["close"] < last["open"]
    if closed_ok:
        score += 40.0

    if not pd.isna(rsi):
        if (bias == "BUY" and rsi > 50) or (bias == "SELL" and rsi < 50):
            score += 25.0

    body  = abs(last["close"] - last["open"])
    full  = last["high"] - last["low"]
    if full > 0:
        wick = 1 - body / full
        score += 25.0 if wick > 0.6 else (10.0 if wick > 0.4 else 0.0)

    vol_ma = last.get("vol_ma20", np.nan)
    if not pd.isna(vol_ma) and vol_ma > 0 and last.get("volume", 0) > vol_ma * 1.2:
        score += 10.0

    return _clip(score)


# ── 7. Risque — CORRECTION CRITIQUE ──────────────────────────────────────────

def score_risk(rrr: float | None, stop_dist_pct: float | None = None) -> float:
    """
    CORRIGÉ : RRR < 2.5 → score 0 (était score partiel, trade pouvait passer).
    """
    if rrr is None or rrr <= 0:
        return 0.0
    if rrr < settings.min_rrr:          # < 2.5 → rejet immédiat
        return 0.0

    rrr_score  = 100.0 if rrr >= 3.0 else 60.0 + (rrr - settings.min_rrr) / (3.0 - settings.min_rrr) * 40.0
    stop_score = 100.0
    if stop_dist_pct is not None:
        if stop_dist_pct > 1.5:   return 0.0
        elif stop_dist_pct > 1.0: stop_score = 50.0
        elif stop_dist_pct > 0.8: stop_score = 80.0

    return _clip((rrr_score + stop_score) / 2)


# ── 8. Macro ──────────────────────────────────────────────────────────────────

def score_macro_context(macro) -> float:
    if macro is None:
        return 50.0
    return _clip(macro.macro_score / 5.0 * 100.0)


# ── 9. On-Chain ───────────────────────────────────────────────────────────────

def score_onchain(macro, bias: str | None) -> float:
    if macro is None or bias is None:
        return 50.0
    fr = getattr(getattr(macro, "onchain", None), "funding_rate_btc", 0.0)
    fg = getattr(getattr(macro, "fear_greed", None), "value", 50)
    score = 50.0

    if bias == "BUY":
        if -0.01 <= fr <= 0.01: score += 25.0
        elif fr < -0.01:        score += 35.0
        elif fr > settings.funding_rate_hot: score -= 40.0
    else:
        if fr > 0.03:    score += 25.0
        elif fr < -0.01: score -= 20.0

    if 30 <= fg <= 70:  score += 15.0
    elif fg < settings.fear_greed_extreme_fear and bias == "BUY":  score -= 20.0
    elif fg > settings.fear_greed_extreme_greed and bias == "BUY": score -= 15.0

    return _clip(score)


# ── Niveaux ───────────────────────────────────────────────────────────────────

def compute_levels(df: pd.DataFrame, bias: str | None
) -> tuple[float | None, float | None, float | None, float | None]:
    if bias is None or len(df) < 20:
        return None, None, None, None
    last = df.iloc[-1]
    w    = df.tail(20)

    if bias == "BUY":
        entry = float(last["close"])
        stop  = float(w["low"].min()) * 0.999
        tp1   = float(w["high"].max())
        dist  = entry - stop
        if dist <= 0: return None, None, None, None
        tp2 = entry + dist * 1.618
    else:
        entry = float(last["close"])
        stop  = float(w["high"].max()) * 1.001
        tp1   = float(w["low"].min())
        dist  = stop - entry
        if dist <= 0: return None, None, None, None
        tp2 = entry - dist * 1.618

    return entry, stop, tp1, tp2


# ── Status ────────────────────────────────────────────────────────────────────

def _status(score: float) -> str:
    if score >= settings.threshold_authorized: return "AUTHORIZED"
    if score >= settings.threshold_watch:      return "WATCH"
    if score >= settings.threshold_weak:       return "WEAK"
    return "REJECTED"


# ── Point d'entrée principal ──────────────────────────────────────────────────

def compute_score(symbol: str, raw_df: pd.DataFrame, macro=None) -> ScoreResult:
    df = compute_indicators(raw_df)

    regime_s, bias     = score_regime(df)
    structure_s        = score_structure(df, bias)
    liquidity_s        = score_liquidity(df, bias)
    pullback_s         = score_pullback(df, bias)
    timing_s, session, ew_start, ew_end = score_timing(df)
    confirmation_s     = score_confirmation(df, bias)
    macro_s            = score_macro_context(macro)
    onchain_s          = score_onchain(macro, bias)

    entry, stop, tp1, tp2 = compute_levels(df, bias)

    rrr           = None
    stop_dist_pct = None
    if entry and stop and tp1 and entry != stop:
        rrr           = round(abs(tp1 - entry) / abs(entry - stop), 2)
        stop_dist_pct = abs(entry - stop) / entry * 100

    risk_s = score_risk(rrr, stop_dist_pct)

    total = round((
        settings.weight_regime        * regime_s
        + settings.weight_structure   * structure_s
        + settings.weight_liquidity   * liquidity_s
        + settings.weight_pullback    * pullback_s
        + settings.weight_timing      * timing_s
        + settings.weight_confirmation * confirmation_s
        + settings.weight_risk        * risk_s
        + settings.weight_macro       * macro_s
        + settings.weight_onchain     * onchain_s
    ) / 100.0, 2)

    status = _status(total)

    macro_ctx = "NEUTRAL"
    if macro is not None:
        macro_ctx = macro.context.value if hasattr(macro.context, "value") else str(macro.context)

    # Blocages structurels
    if bias is None and status == "AUTHORIZED":       status = "WATCH"
    if timing_s == 0.0 and status == "AUTHORIZED":    status = "WATCH"
    if macro_ctx == "CRISIS":                          status = "REJECTED"

    reasons = _build_reasons(bias, regime_s, structure_s, liquidity_s,
                              pullback_s, timing_s, confirmation_s,
                              risk_s, rrr, session, macro)

    return ScoreResult(
        symbol=symbol, direction=bias or "NONE",
        sub_scores=SubScores(
            regime=regime_s, structure=structure_s, liquidity=liquidity_s,
            pullback=pullback_s, timing=timing_s, confirmation=confirmation_s,
            risk=risk_s, macro=macro_s, onchain=onchain_s, reasons=reasons,
        ),
        total_score=total, status=status,
        entry_price=entry, stop_loss=stop, tp1=tp1, tp2=tp2, rrr=rrr,
        reasons=reasons,
        session_name=session,
        entry_window_start=ew_start,
        entry_window_end=ew_end,
        macro_context=macro_ctx,
    )


def _build_reasons(bias, regime, structure, liquidity, pullback,
                   timing, confirmation, risk, rrr, session, macro) -> list[str]:
    r = []
    if bias:                r.append(f"Biais {bias} confirmé")
    if regime >= 70:        r.append("Régime tendance net (ADX élevé)")
    if structure >= 85:     r.append("BOS + structure confirmée (HH/HL ou LH/LL)")
    elif structure >= 65:   r.append("Cassure de structure partielle")
    if liquidity >= 85:     r.append("Sweep de liquidité détecté (BSL/SSL)")
    elif liquidity >= 70:   r.append("Fair Value Gap identifié")
    if pullback >= 85:      r.append("Pullback zone Fibonacci optimale (38.2–78.6%)")
    if session:             r.append(f"Session active : {session}")
    if confirmation >= 80:  r.append("Confirmation forte : clôture + volume + wick")
    elif confirmation >= 55: r.append("Confirmation partielle")
    if rrr and rrr >= settings.min_rrr:
                            r.append(f"R:R {rrr:.2f} — ratio valide")
    if macro is not None:
        ctx = macro.context.value if hasattr(macro.context, "value") else str(macro.context)
        fg  = getattr(getattr(macro, "fear_greed", None), "value", "?")
        r.append(f"Macro : {ctx} (F&G {fg})")
    if not r:
        r.append("Aucun facteur fort sur ce cycle")
    return r
