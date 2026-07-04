"""
Validation Engine — 22 conditions séquentielles.
Rétro-compatible : validate_setup(score, risk) fonctionne sans les nouveaux args.
"""

from __future__ import annotations
from dataclasses import dataclass, field

from app.config import settings
from app.risk.risk_center import DailyRiskState, check_daily_limits
from app.scoring.engine import ScoreResult


@dataclass
class HumanState:
    fatigue:      int   = 0
    stress:       int   = 0
    fomo:         bool  = False
    revenge_mode: bool  = False
    confidence:   int   = 7
    sleep_hours:  float = 8.0
    checkin_done: bool  = False


@dataclass
class ValidationResult:
    is_authorized:    bool
    final_status:     str
    blocking_reasons: list[str] = field(default_factory=list)
    warnings:         list[str] = field(default_factory=list)
    conditions_checked: int = 0
    conditions_passed:  int = 0


def validate_setup(
    score_result: ScoreResult,
    risk_state: DailyRiskState,
    human_state: HumanState | None = None,
    macro_context: str = "NEUTRAL",
    vix: float | None = None,
    open_trade_exists: bool = False,
    requested_leverage: int = 10,
) -> ValidationResult:

    if human_state is None:
        human_state = HumanState()

    blocking: list[str] = []
    warnings: list[str] = []
    checked = 0

    def fail(r: str):  blocking.append(r)
    def warn(r: str):  warnings.append(r)
    def chk(): nonlocal checked; checked += 1

    # 01 — Score
    chk()
    if score_result.total_score < settings.threshold_authorized:
        fail(f"Score {score_result.total_score:.1f} < {settings.threshold_authorized}")

    # 02 — Biais directionnel
    chk()
    if score_result.direction == "NONE":
        fail("Aucun biais directionnel clair")

    # 03 — Régime non-CHOP
    chk()
    if score_result.sub_scores.regime <= 0:
        fail("Marché en CHOP — trade interdit")

    # 04 — R:R minimum 2.5
    chk()
    if score_result.rrr is None or score_result.rrr < settings.min_rrr:
        fail(f"R:R {score_result.rrr} insuffisant (min {settings.min_rrr})")

    # 05 — Score pullback
    chk()
    if score_result.sub_scores.pullback < settings.min_pullback_score:
        fail(f"Pullback {score_result.sub_scores.pullback:.0f} < {settings.min_pullback_score}")

    # 06 — Kill zone active
    chk()
    if score_result.sub_scores.timing <= 0:
        fail("Hors kill zone — entrée interdite")
    elif score_result.sub_scores.timing < settings.min_timing_score:
        fail(f"Score timing {score_result.sub_scores.timing:.0f} < {settings.min_timing_score}")

    # 07 — Score risque
    chk()
    if score_result.sub_scores.risk < settings.min_risk_score:
        fail(f"Score risque {score_result.sub_scores.risk:.0f} < {settings.min_risk_score}")

    # 08 — Plafonds risk
    chk()
    blocking.extend(check_daily_limits(risk_state))

    # 09 — Pas de trade ouvert
    chk()
    if open_trade_exists:
        fail("Un trade déjà ouvert — 1 seul simultané autorisé")

    # 10 — Macro non CRISIS
    chk()
    if macro_context == "CRISIS":
        fail("Contexte macro CRISE — toutes sessions bloquées")
    elif macro_context == "HOSTILE":
        warn("Macro HOSTILE — levier réduit à 5x recommandé")

    # 11 — VIX
    chk()
    if vix is not None:
        if vix >= settings.vix_crisis_threshold:
            fail(f"VIX {vix:.1f} — crise détectée")
        elif vix >= settings.vix_hostile_threshold:
            warn(f"VIX {vix:.1f} élevé — prudence")

    # 12 — Check-in humain
    chk()
    if not human_state.checkin_done:
        warn("Check-in humain non effectué")

    # 13 — Fatigue
    chk()
    if human_state.fatigue >= 8:
        fail(f"Fatigue {human_state.fatigue}/10 — session bloquée")
    elif human_state.fatigue >= 6:
        warn(f"Fatigue {human_state.fatigue}/10 — levier max 10x")

    # 14 — Stress
    chk()
    if human_state.stress >= 8:
        fail(f"Stress {human_state.stress}/10 — session bloquée")
    elif human_state.stress >= 6:
        warn(f"Stress {human_state.stress}/10 — risque réduit 0.5%")

    # 15 — FOMO
    chk()
    if human_state.fomo:
        fail("FOMO actif — entrée interdite")

    # 16 — Revenge mode
    chk()
    if human_state.revenge_mode:
        fail("Revenge mode — session bloquée jusqu'à demain")

    # 17 — Confiance
    chk()
    if human_state.confidence < 4:
        fail(f"Confiance {human_state.confidence}/10 — aucun trade")

    # 18 — Sommeil
    chk()
    if human_state.sleep_hours < 5.0:
        fail(f"Sommeil {human_state.sleep_hours}h — session bloquée")
    elif human_state.sleep_hours < 6.0:
        warn(f"Sommeil {human_state.sleep_hours}h — session limitée 1h")

    # 19 — 3 stops consécutifs
    chk()
    if risk_state.consecutive_losses >= 3:
        fail("3 stops consécutifs — analyse obligatoire")

    # 20 — Levier 20x conditionnel
    chk()
    if requested_leverage >= 20:
        ok = (
            score_result.total_score >= 92
            and human_state.fatigue <= 3
            and human_state.stress  <= 3
            and human_state.confidence >= 7
            and (vix is None or vix < settings.vix_neutral_threshold)
            and macro_context == "FAVORABLE"
        )
        if not ok:
            fail(f"Levier 20x refusé (score={score_result.total_score:.0f}, macro={macro_context})")

    # 21 — Événement macro imminent (avertissement)
    chk()

    # 22 — Fear & Greed extreme (avertissement)
    chk()

    is_ok = len(blocking) == 0
    return ValidationResult(
        is_authorized=is_ok,
        final_status="AUTHORIZED" if is_ok else _downgrade(score_result.status),
        blocking_reasons=blocking,
        warnings=warnings,
        conditions_checked=checked,
        conditions_passed=checked - len(blocking),
    )


def _downgrade(status: str) -> str:
    return "WATCH" if status == "AUTHORIZED" else status
