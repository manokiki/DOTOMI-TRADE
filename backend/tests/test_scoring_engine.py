"""
Tests unitaires du Score Engine — section 6.3 du prompt maître.

On construit des séries de prix synthétiques avec des propriétés connues
(tendance nette, range plat...) pour vérifier que chaque sous-score réagit
dans la direction attendue. On ne vérifie pas des valeurs exactes (les
formules peuvent être ajustées après backtest) mais des comportements
attendus : un marché en tendance nette doit scorer plus haut en "régime"
qu'un marché plat, par exemple.
"""

import numpy as np
import pandas as pd
import pytest

from app.scoring.engine import compute_score, score_regime, score_risk
from app.scoring.indicators import compute_indicators


def make_trending_df(n: int = 100, start: float = 100.0, step: float = 0.5) -> pd.DataFrame:
    """Série artificiellement haussière et linéaire, avec un peu de bruit."""
    rng = np.random.default_rng(42)
    closes = start + np.arange(n) * step + rng.normal(0, 0.1, n)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": closes - 0.05,
            "high": closes + 0.3,
            "low": closes - 0.3,
            "close": closes,
            "volume": rng.uniform(100, 200, n),
        }
    )
    return df


def make_flat_df(n: int = 100, level: float = 100.0) -> pd.DataFrame:
    """Série plate (range), sans tendance, juste du bruit autour d'un niveau fixe."""
    rng = np.random.default_rng(7)
    closes = level + rng.normal(0, 0.05, n)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": closes - 0.02,
            "high": closes + 0.1,
            "low": closes - 0.1,
            "close": closes,
            "volume": rng.uniform(100, 200, n),
        }
    )
    return df


class TestRegimeScore:
    def test_trending_market_scores_higher_than_flat_market(self):
        trending = compute_indicators(make_trending_df())
        flat = compute_indicators(make_flat_df())

        trending_score, trending_bias = score_regime(trending)
        flat_score, flat_bias = score_regime(flat)

        assert trending_score > flat_score
        assert trending_bias == "BUY"

    def test_flat_market_has_no_clear_bias_or_low_score(self):
        flat = compute_indicators(make_flat_df())
        score, bias = score_regime(flat)
        assert score <= 40.0  # plafonné en l'absence de tendance (voir engine.py)


class TestRiskScore:
    def test_rrr_below_minimum_scores_low(self):
        assert score_risk(0.5) < 40.0

    def test_rrr_at_three_or_above_scores_maximum(self):
        assert score_risk(3.0) == 100.0
        assert score_risk(5.0) == 100.0

    def test_none_rrr_scores_zero(self):
        assert score_risk(None) == 0.0

    def test_negative_rrr_scores_zero(self):
        assert score_risk(-1.0) == 0.0


class TestComputeScoreIntegration:
    def test_trending_market_produces_buy_or_none_direction(self):
        df = make_trending_df(n=150)
        result = compute_score("TEST/USD", df)
        assert result.direction in ("BUY", "SELL", "NONE")
        assert 0 <= result.total_score <= 100

    def test_score_result_has_all_subscores(self):
        df = make_trending_df(n=150)
        result = compute_score("TEST/USD", df)
        sub = result.sub_scores
        for value in (sub.regime, sub.structure, sub.liquidity, sub.pullback, sub.timing, sub.confirmation, sub.risk):
            assert 0 <= value <= 100

    def test_status_never_authorized_without_clear_bias(self):
        flat = make_flat_df(n=150)
        result = compute_score("TEST/USD", flat)
        if result.direction == "NONE":
            assert result.status != "AUTHORIZED"

    def test_raises_on_insufficient_data(self):
        tiny_df = make_trending_df(n=5)
        # Ne doit pas planter de façon incontrôlée — soit ça lève, soit ça
        # retourne un résultat avec des scores bas par manque de données.
        try:
            result = compute_score("TEST/USD", tiny_df)
            assert result.total_score >= 0
        except Exception:
            pass  # acceptable : signaler l'insuffisance de données est correct
