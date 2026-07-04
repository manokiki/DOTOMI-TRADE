"""
Alerting par email — section 7 du prompt maître.

Déclenché uniquement quand un setup passe au statut AUTHORIZED. Contient
tout ce qui est nécessaire pour décider sans ouvrir le dashboard : actif,
sens, score, niveaux, fenêtre horaire, raisons, risque calculé.

Robustesse : retry avec backoff exponentiel sur l'envoi SMTP (même logique
que pour les appels aux APIs de marché, section 6.1) — une alerte ne doit
jamais être perdue silencieusement parce que le serveur SMTP a eu un hoquet.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.risk.risk_center import PositionSizing
from app.scoring.engine import ScoreResult

logger = logging.getLogger("dotomi.alerting")


def render_trade_alert_html(score_result: ScoreResult, sizing: PositionSizing | None) -> str:
    reasons_html = "".join(f"<li>{r}</li>" for r in score_result.reasons)
    sizing_html = ""
    if sizing:
        sizing_html = f"""
        <tr><td><b>Quantité suggérée</b></td><td>{sizing.quantity:.6f}</td></tr>
        <tr><td><b>Risque ($)</b></td><td>{sizing.risk_amount:.2f}</td></tr>
        <tr><td><b>Risque (%)</b></td><td>{sizing.risk_pct_used:.2f}%</td></tr>
        """

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #1c1c1a; background: #faf9f6; padding: 20px;">
      <h2 style="color: #173404;">Trade autorisé — {score_result.symbol}</h2>
      <table style="border-collapse: collapse; width: 100%; max-width: 480px;">
        <tr><td><b>Sens</b></td><td>{score_result.direction}</td></tr>
        <tr><td><b>Score total</b></td><td>{score_result.total_score:.1f}/100</td></tr>
        <tr><td><b>Statut</b></td><td>{score_result.status}</td></tr>
        <tr><td><b>Entrée</b></td><td>{score_result.entry_price}</td></tr>
        <tr><td><b>Stop-loss</b></td><td>{score_result.stop_loss}</td></tr>
        <tr><td><b>TP1</b></td><td>{score_result.tp1}</td></tr>
        <tr><td><b>TP2</b></td><td>{score_result.tp2}</td></tr>
        <tr><td><b>Ratio risque/rendement</b></td><td>{score_result.rrr}</td></tr>
        {sizing_html}
      </table>
      <h3>Pourquoi</h3>
      <ul>{reasons_html}</ul>
      <p style="color: #5f5e5a; font-size: 12px;">
        Cette alerte est générée automatiquement par DOTOMI-TRADE à partir de
        règles déterministes. Elle ne constitue pas un conseil financier et
        la décision finale d'exécution reste entièrement humaine.
      </p>
    </body>
    </html>
    """


async def send_email_with_retry(subject: str, html_body: str, to_address: str | None = None) -> bool:
    """
    Envoie un email avec retry + backoff exponentiel. Retourne True si
    l'envoi a réussi, False si toutes les tentatives ont échoué (dans ce
    cas, l'appelant est responsable de journaliser l'échec dans
    SystemHealthLog — voir section 6.2).
    """
    if not settings.alerts_enabled:
        logger.info("alerts_disabled_skip_send", extra={"subject": subject})
        return False

    to_address = to_address or settings.alert_email_to
    if not to_address:
        logger.error("alert_email_to_not_configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to_address
    msg.attach(MIMEText(html_body, "html"))

    last_exc: Exception | None = None
    for attempt in range(1, settings.retry_max_attempts + 1):
        try:
            await asyncio.to_thread(_send_sync, msg, to_address)
            logger.info("alert_email_sent", extra={"subject": subject, "to": to_address})
            return True
        except Exception as exc:  # noqa: BLE001 — on veut tout intercepter pour le retry
            last_exc = exc
            delay = settings.retry_base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "alert_email_send_failed",
                extra={"attempt": attempt, "delay": delay, "error": str(exc)},
            )
            if attempt < settings.retry_max_attempts:
                await asyncio.sleep(delay)

    logger.error("alert_email_send_exhausted", extra={"error": str(last_exc)})
    return False


def _send_sync(msg: MIMEMultipart, to_address: str) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_user, [to_address], msg.as_string())


async def send_trade_alert(score_result: ScoreResult, sizing: PositionSizing | None = None) -> bool:
    subject = f"[DOTOMI-TRADE] {score_result.symbol} {score_result.direction} — score {score_result.total_score:.0f}"
    html = render_trade_alert_html(score_result, sizing)
    return await send_email_with_retry(subject, html)


async def send_system_down_alert(component: str, error_message: str) -> bool:
    """
    Alerting OPÉRATIONNEL distinct de l'alerting trading (section 6.2) :
    prévient l'utilisateur que c'est le système qui est en panne, pas
    l'absence de bon trade.
    """
    subject = f"[DOTOMI-TRADE] Alerte système — {component} en panne"
    html = f"""
    <html><body style="font-family: Arial, sans-serif;">
    <h2 style="color: #791F1F;">Composant en panne : {component}</h2>
    <p>{error_message}</p>
    <p style="color: #5f5e5a; font-size: 12px;">
      Le silence du système pendant cette panne ne signifie pas l'absence
      de bon trade — il signifie que le système ne fonctionne pas
      correctement actuellement.
    </p>
    </body></html>
    """
    return await send_email_with_retry(subject, html)
