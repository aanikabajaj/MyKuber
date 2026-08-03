"""Notification delivery — Email OTP (SMTP) and SMS OTP (Twilio / Fast2SMS).

Provider priority
-----------------
Email:  SMTP (any provider: Gmail, Outlook, Zoho, custom)
SMS:    Twilio  →  Fast2SMS (India free tier)  →  console/dev fallback

Going live
----------
Fill in the relevant env vars in backend/.env (or system env).
DEMO_MODE can remain ``true`` while credentials are set — OTP codes will
still be sent to the real destination AND surfaced in the API response
so the demo console keeps working.

Set IAARE_DEMO_MODE=false for a fully silent production deployment.
"""
from __future__ import annotations

import smtplib
import ssl
import time
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("iaare.notify")

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class DeliveryResult:
    channel: str            # 'email' | 'sms'
    destination: str
    provider: str           # 'smtp' | 'twilio' | 'fast2sms' | 'console'
    delivered: bool
    dev_code: Optional[str] = None   # populated in DEMO_MODE regardless of provider


# ---------------------------------------------------------------------------
# Provider availability checks
# ---------------------------------------------------------------------------

def twilio_configured() -> bool:
    return bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_FROM_NUMBER
    )


def fast2sms_configured() -> bool:
    return bool(settings.FAST2SMS_API_KEY)


def sms_configured() -> bool:
    return twilio_configured() or fast2sms_configured()


def email_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def active_providers() -> dict:
    sms_prov = (
        "twilio (LIVE)" if twilio_configured()
        else "fast2sms (LIVE)" if fast2sms_configured()
        else "console/dev"
    )
    email_prov = "smtp (LIVE)" if email_configured() else "console/dev"
    return {"sms": sms_prov, "email": email_prov}


# ---------------------------------------------------------------------------
# HTML email template
# ---------------------------------------------------------------------------

def _html_email(code: str, ttl_minutes: int, purpose: str = "verification") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>IAARE Verification Code</title>
</head>
<body style="margin:0;padding:0;background:#0a0e1a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0e1a;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0"
               style="background:#141b2d;border-radius:16px;border:1px solid #232c42;overflow:hidden;">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:28px 32px;">
              <div style="font-size:22px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">
                🛡️ IAARE · Punjab &amp; Sind Bank
              </div>
              <div style="font-size:13px;color:#c7d2fe;margin-top:4px;">
                Intelligent Adaptive Authentication
              </div>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <p style="color:#94a3b8;font-size:14px;margin:0 0 20px;">
                Your {purpose} code is:
              </p>
              <!-- OTP box -->
              <div style="text-align:center;margin:24px 0;">
                <div style="display:inline-block;background:#1e2a45;border:2px solid #6366f1;
                            border-radius:12px;padding:18px 40px;">
                  <span style="font-size:40px;font-weight:900;color:#6366f1;
                               letter-spacing:12px;font-family:monospace;">{code}</span>
                </div>
              </div>
              <p style="color:#94a3b8;font-size:13px;text-align:center;margin:0 0 24px;">
                This code is valid for <strong style="color:#f1f5f9;">{ttl_minutes} minutes</strong>.
                Do not share it with anyone.
              </p>
              <hr style="border:none;border-top:1px solid #232c42;margin:24px 0;" />
              <p style="color:#64748b;font-size:12px;margin:0;">
                If you did not request this code, please ignore this email or contact
                your branch immediately. Punjab &amp; Sind Bank will never ask for
                your OTP over phone or email.
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background:#111726;padding:16px 32px;border-top:1px solid #232c42;">
              <p style="color:#475569;font-size:11px;margin:0;text-align:center;">
                Punjab &amp; Sind Bank · Automated Security Alert · Do not reply
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# EMAIL — SMTP with TLS/SSL auto-detection and retry
# ---------------------------------------------------------------------------

def _smtp_send(destination: str, subject: str, plain: str, html: str) -> None:
    """Send a multipart email. Tries STARTTLS on port 587/25, SSL on port 465."""
    from_addr = settings.SMTP_FROM or f"IAARE Security <{settings.SMTP_USER}>"

    msg = MIMEMultipart("alternative")
    msg["From"]    = from_addr
    msg["To"]      = destination
    msg["Subject"] = subject
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))

    port = int(settings.SMTP_PORT)

    # Port 465 → implicit SSL; everything else → STARTTLS
    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, port, context=context, timeout=20) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [destination], msg.as_string())
    else:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [destination], msg.as_string())


def send_email_otp(destination: str, code: str, purpose: str = "verification") -> DeliveryResult:
    """Send an OTP via SMTP. Falls back to console if SMTP not configured."""
    ttl_min  = settings.OTP_TTL_SECONDS // 60
    subject  = f"Your IAARE {purpose} code: {code}"
    plain    = (
        f"Your IAARE (Punjab & Sind Bank) {purpose} code is: {code}\n\n"
        f"This code expires in {ttl_min} minutes.\n"
        "Do not share this code with anyone.\n\n"
        "If you did not request this, please ignore this message."
    )
    html = _html_email(code, ttl_min, purpose)

    if email_configured():
        last_exc: Exception | None = None
        for attempt in range(2):          # 1 retry on transient failures
            try:
                _smtp_send(destination, subject, plain, html)
                logger.info("email_otp_sent provider=smtp to=%s attempt=%d", destination, attempt + 1)
                return DeliveryResult(
                    "email", destination, "smtp", True,
                    dev_code=code if settings.DEMO_MODE else None,
                )
            except smtplib.SMTPAuthenticationError as exc:
                logger.error("email_otp_smtp_auth_failed: %s", exc)
                break   # no point retrying auth failures
            except Exception as exc:
                last_exc = exc
                logger.warning("email_otp_smtp_attempt_%d_failed: %s", attempt + 1, exc)
                if attempt == 0:
                    time.sleep(1)

        logger.error("email_otp_smtp_all_attempts_failed: %s — falling back to console", last_exc)

    # Console / dev fallback
    logger.info("[DEV EMAIL OTP] to=%s code=%s", destination, code)
    return DeliveryResult(
        "email", destination, "console", True,
        dev_code=code if settings.DEMO_MODE else None,
    )


# ---------------------------------------------------------------------------
# SMS — Twilio
# ---------------------------------------------------------------------------

def _twilio_send(destination: str, body: str) -> None:
    """Send SMS via Twilio REST API."""
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    )
    resp = httpx.post(
        url,
        data={
            "From": settings.TWILIO_FROM_NUMBER,
            "To":   destination,
            "Body": body,
        },
        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") in ("failed", "undelivered"):
        raise RuntimeError(
            f"Twilio message status={data.get('status')} "
            f"error_code={data.get('error_code')} "
            f"error_message={data.get('error_message')}"
        )


# ---------------------------------------------------------------------------
# SMS — Fast2SMS (India, free tier: https://www.fast2sms.com)
# Route: Quick SMS (DLT not required for OTP route)
# ---------------------------------------------------------------------------

def _fast2sms_send(destination: str, body: str) -> None:
    """Send SMS via Fast2SMS Quick SMS API (Indian numbers only).

    destination: 10-digit Indian mobile number (e.g. '9812345678').
                 Strips leading +91 / 91 automatically.
    """
    # Strip country code if present
    number = destination.lstrip("+")
    if number.startswith("91") and len(number) == 12:
        number = number[2:]
    if not (number.isdigit() and len(number) == 10):
        raise ValueError(f"Fast2SMS requires a 10-digit Indian number, got: {destination!r}")

    resp = httpx.post(
        "https://www.fast2sms.com/dev/bulkV2",
        headers={
            "authorization": settings.FAST2SMS_API_KEY,
            "Content-Type":  "application/json",
        },
        json={
            "route":   "q",          # Quick SMS — no DLT required
            "message": body,
            "language": "english",
            "flash":    0,
            "numbers":  number,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("return", False):
        raise RuntimeError(f"Fast2SMS error: {data.get('message', data)}")


# ---------------------------------------------------------------------------
# Unified SMS entry point
# ---------------------------------------------------------------------------

def send_sms_otp(destination: str, code: str) -> DeliveryResult:
    """Send OTP via SMS.  Provider priority: Twilio → Fast2SMS → console."""
    body = f"IAARE OTP: {code}. Valid {settings.OTP_TTL_SECONDS // 60} min. Do NOT share. -Punjab & Sind Bank"

    # --- Try Twilio ---
    if twilio_configured():
        try:
            _twilio_send(destination, body)
            logger.info("sms_otp_sent provider=twilio to=%s", destination)
            return DeliveryResult(
                "sms", destination, "twilio", True,
                dev_code=code if settings.DEMO_MODE else None,
            )
        except Exception as exc:
            logger.warning("sms_otp_twilio_failed: %s — trying fallback", exc)

    # --- Try Fast2SMS ---
    if fast2sms_configured():
        try:
            _fast2sms_send(destination, body)
            logger.info("sms_otp_sent provider=fast2sms to=%s", destination)
            return DeliveryResult(
                "sms", destination, "fast2sms", True,
                dev_code=code if settings.DEMO_MODE else None,
            )
        except Exception as exc:
            logger.warning("sms_otp_fast2sms_failed: %s — falling back to console", exc)

    # --- Console fallback ---
    logger.info("[DEV SMS OTP] to=%s code=%s", destination, code)
    return DeliveryResult(
        "sms", destination, "console", True,
        dev_code=code if settings.DEMO_MODE else None,
    )
