"""
Tests unitaires du Risk Center — sizing et plafonds (section 5.2 et 5.3).
"""

import pytest

from app.risk.risk_center import (
    DailyRiskState,
    compute_position_size,
    check_daily_limits,
)


class TestPositionSizing:
    def test_basic_sizing_respects_risk_budget(self):
        sizing = compute_position_size(
            capital=100.0, entry_price=61250, stop_loss=61020, atr=None, risk_pct=1.0
        )
        # risk_budget = 100 * 1% = 1$. distance = 230. quantité = 1/230.
        expected_qty = 1.0 / 230
        assert sizing.quantity == pytest.approx(expected_qty, rel=1e-6)
        assert sizing.risk_amount == pytest.approx(1.0)
        assert sizing.method_used == "stop_distance"

    def test_atr_method_used_when_more_conservative(self):
        # ATR très large -> la méthode ATR donne une quantité plus petite,
        # donc c'est elle qui doit être retenue (la plus conservatrice).
        sizing = compute_position_size(
            capital=100.0, entry_price=100.0, stop_loss=99.0, atr=10.0, risk_pct=1.0
        )
        assert sizing.method_used == "atr"

    def test_risk_pct_above_safety_cap_is_capped(self):
        sizing = compute_position_size(
            capital=100.0, entry_price=100.0, stop_loss=99.0, atr=None, risk_pct=50.0
        )
        assert sizing.capped_by_safety_limit is True
        assert sizing.risk_pct_used <= 10.0  # hard_safety_cap_daily_loss_pct par défaut

    def test_zero_stop_distance_raises(self):
        with pytest.raises(ValueError):
            compute_position_size(capital=100.0, entry_price=100.0, stop_loss=100.0, atr=None)


class TestDailyLimits:
    def test_no_blocks_when_within_limits(self):
        state = DailyRiskState(capital=100.0, daily_pnl=-1.0, weekly_pnl=-2.0, trades_taken_today=1)
        blocks = check_daily_limits(state)
        assert blocks == []

    def test_blocks_when_daily_loss_exceeded(self):
        state = DailyRiskState(capital=100.0, daily_pnl=-6.0, weekly_pnl=0.0, trades_taken_today=1)
        blocks = check_daily_limits(state)
        assert any("journalière" in b for b in blocks)

    def test_blocks_when_max_trades_reached(self):
        state = DailyRiskState(capital=100.0, daily_pnl=0.0, weekly_pnl=0.0, trades_taken_today=5)
        blocks = check_daily_limits(state)
        assert any("trades journaliers" in b for b in blocks)
