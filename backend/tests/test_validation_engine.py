"""
Tests unitaires du Validation Engine — règles obligatoires (section 5.1).
"""

from app.risk.risk_center import DailyRiskState
from app.risk.validation import validate_setup
from app.scoring.engine import ScoreResult, SubScores


def make_score_result(**overrides) -> ScoreResult:
    defaults = dict(
        symbol="TEST/USD",
        direction="BUY",
        sub_scores=SubScores(
            regime=90, structure=90, liquidity=90, pullback=90,
            timing=90, confirmation=90, risk=90,
        ),
        total_score=90.0,
        status="AUTHORIZED",
        entry_price=100.0,
        stop_loss=98.0,
        tp1=104.0,
        tp2=108.0,
        rrr=2.0,
        reasons=["test"],
    )
    defaults.update(overrides)
    return ScoreResult(**defaults)


def make_clean_risk_state() -> DailyRiskState:
    return DailyRiskState(capital=100.0, daily_pnl=0.0, weekly_pnl=0.0, trades_taken_today=0)


class TestValidationRules:
    def test_strong_setup_with_clean_risk_state_is_authorized(self):
        result = validate_setup(make_score_result(), make_clean_risk_state())
        assert result.is_authorized is True
        assert result.blocking_reasons == []

    def test_no_direction_blocks_authorization(self):
        score = make_score_result(direction="NONE")
        result = validate_setup(score, make_clean_risk_state())
        assert result.is_authorized is False
        assert any("biais" in r.lower() for r in result.blocking_reasons)

    def test_low_total_score_blocks_authorization(self):
        score = make_score_result(total_score=60.0)
        result = validate_setup(score, make_clean_risk_state())
        assert result.is_authorized is False

    def test_low_rrr_blocks_authorization(self):
        score = make_score_result(rrr=0.5)
        result = validate_setup(score, make_clean_risk_state())
        assert result.is_authorized is False

    def test_daily_loss_limit_blocks_even_strong_setup(self):
        risky_state = DailyRiskState(capital=100.0, daily_pnl=-10.0, weekly_pnl=0.0, trades_taken_today=0)
        result = validate_setup(make_score_result(), risky_state)
        assert result.is_authorized is False

    def test_blocked_setup_never_reports_authorized_status(self):
        score = make_score_result(direction="NONE")
        result = validate_setup(score, make_clean_risk_state())
        assert result.final_status != "AUTHORIZED"
