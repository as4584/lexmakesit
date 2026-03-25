"""
SendGrid email service.

Handles transactional emails: verification, password reset, welcome.
Reads SENDGRID_API and FROM_EMAIL from settings/environment.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_settings():
    from ai_receptionist.config.settings import get_settings
    return get_settings()


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send a transactional email via SendGrid.

    Returns True on success, False on failure (logs the error).
    """
    settings = _get_settings()
    api_key = settings.sendgrid_api
    from_email = settings.from_email

    if not api_key:
        logger.error("SENDGRID_API not configured — cannot send email")
        return False

    try:
        import urllib.request
        import json

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_email, "name": "Lex Makes It"},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 202):
                logger.info(f"Email sent to {to_email}: {subject}")
                return True
            else:
                logger.error(f"SendGrid returned {resp.status} for {to_email}")
                return False
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_verification_email(to_email: str, token: str) -> bool:
    settings = _get_settings()
    verify_url = f"{settings.app_base_url}/auth/verify-email?token={token}"

    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Inter, sans-serif; background: #f5f5f5; padding: 40px;">
  <div style="max-width: 480px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
    <h1 style="font-size: 1.5rem; color: #111; margin-bottom: 0.5rem;">Verify your email</h1>
    <p style="color: #555; margin-bottom: 2rem;">
      Click the button below to verify your email and set up your password.
      This link expires in <strong>24 hours</strong>.
    </p>
    <a href="{verify_url}"
       style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #60aaff, #3d84ff);
              color: white; text-decoration: none; border-radius: 12px; font-weight: bold; font-size: 1rem;">
      Verify Email & Set Password
    </a>
    <p style="margin-top: 2rem; color: #999; font-size: 0.85rem;">
      If you didn't create an account, you can safely ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 2rem 0;">
    <p style="color: #bbb; font-size: 0.8rem;">Lex Makes It · lexmakesit.com</p>
  </div>
</body>
</html>"""

    return send_email(to_email, "Verify your email — Lex Makes It", html)


def send_password_reset_email(to_email: str, token: str) -> bool:
    settings = _get_settings()
    reset_url = f"{settings.app_base_url}/auth/reset-password?token={token}"

    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Inter, sans-serif; background: #f5f5f5; padding: 40px;">
  <div style="max-width: 480px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
    <h1 style="font-size: 1.5rem; color: #111; margin-bottom: 0.5rem;">Reset your password</h1>
    <p style="color: #555; margin-bottom: 2rem;">
      We received a request to reset your password. Click the button below.
      This link expires in <strong>1 hour</strong>.
    </p>
    <a href="{reset_url}"
       style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #60aaff, #3d84ff);
              color: white; text-decoration: none; border-radius: 12px; font-weight: bold; font-size: 1rem;">
      Reset Password
    </a>
    <p style="margin-top: 2rem; color: #999; font-size: 0.85rem;">
      If you didn't request a password reset, you can safely ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 2rem 0;">
    <p style="color: #bbb; font-size: 0.8rem;">Lex Makes It · lexmakesit.com</p>
  </div>
</body>
</html>"""

    return send_email(to_email, "Reset your password — Lex Makes It", html)
