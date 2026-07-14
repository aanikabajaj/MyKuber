"""Notification delivery abstraction for OTP codes.

Design goal (per project brief): isolate SMS/Email providers behind a single
interface so that going live only requires adding credentials — the rest of the
application is untouched. When no provider credentials are configured the
service falls back to *console/dev delivery*: it logs the code and (in
DEMO_MODE) returns it to the caller so the live demo works without any external
account.
"""
from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("iaare.notify")


@dataclass
class DeliveryResult:
    channel: str            # 'email' | 'sms'
    destination: str
    provider: str           # 'smtp' | 'twilio' | 'console'
    delivered: bool
    dev_code: Optional[str] = None  # populated only in DEMO_MODE


# --------------------------------------------------------------------------- #
#  EMAIL
# --------------------------------------------------------------------------- #
def _send_email_smtp(destination: str, subject: str, body: str) -> bool:
    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = destination
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, destination, msg.as_string())
    return True


def send_email_otp(destination: str, code: str) -> DeliveryResult:
    subject = "Your IAARE verification code"
    body = (
        f"Your IAARE (Punjab & Sind Bank) verification code is: {code}\n\n"
        f"This code expires in {settings.OTP_TTL_SECONDS // 60} minutes.\n"
        "If you did not request this, please ignore this message."
    )
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            _send_email_smtp(destination, subject, body)
            logger.info("Email OTP sent to %s via SMTP", destination)
            return DeliveryResult("email", destination, "smtp", True)
        except Exception as exc:  # noqa: BLE001  (fall back gracefully in a prototype)
            logger.warning("SMTP delivery failed (%s); falling back to console", exc)

    logger.info("[DEV EMAIL OTP] to=%s code=%s", destination, code)
    return DeliveryResult(
        "email", destination, "console", True,
        dev_code=code if settings.DEMO_MODE else None,
    )


# --------------------------------------------------------------------------- #
#  SMS
# --------------------------------------------------------------------------- #
def _send_sms_twilio(destination: str, body: str) -> bool:
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    )
    resp = httpx.post(
        url,
        data={
            "From": settings.TWILIO_FROM_NUMBER,
            "To": destination,
            "Body": body,
        },
        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
        timeout=15,
    )
    resp.raise_for_status()
    return True


def send_sms_otp(destination: str, code: str) -> DeliveryResult:
    body = f"IAARE: your verification code is {code}. Valid for 5 minutes."
    if (
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_FROM_NUMBER
    ):
        try:
            _send_sms_twilio(destination, body)
            logger.info("SMS OTP sent to %s via Twilio", destination)
            return DeliveryResult("sms", destination, "twilio", True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Twilio delivery failed (%s); falling back to console", exc)

    logger.info("[DEV SMS OTP] to=%s code=%s", destination, code)
    return DeliveryResult(
        "sms", destination, "console", True,
        dev_code=code if settings.DEMO_MODE else None,
    )
