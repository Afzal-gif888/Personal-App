"""Account emails, sent through EmailJS: the login OTP and the password-reset link."""

import logging
from datetime import timedelta

from app.core.config import get_settings
from app.core.security import create_email_token
from app.models import User
from app.notifications.emailjs import EmailError, send_template

logger = logging.getLogger(__name__)

RESET_TTL = timedelta(minutes=30)


def send_login_otp(user: User, otp: str) -> None:
    """Email the 6-digit code with the OTP template ({{name}}, {{otp}}). Raises EmailError."""
    send_template(get_settings().emailjs_template_id, user.email, user.name, {"otp": otp})


def send_password_reset_email(user: User) -> bool:
    """Best effort: an unreachable email service never reveals whether the account exists."""
    s = get_settings()
    link = f"{s.app_base_url.rstrip('/')}/reset-password?token={create_email_token(user, 'reset_password', RESET_TTL)}"
    message = (
        "Someone (hopefully you) asked to reset your It's Personal password. Choose a new one here:\n\n"
        f"{link}\n\n"
        "The link works once and expires in 30 minutes. If you didn't ask for this, ignore this email; "
        "your password stays the same."
    )
    try:
        send_template(s.emailjs_notification_template_id, user.email, user.name,
                      {"subject": "Reset your It's Personal password", "message": message})
        return True
    except EmailError:
        return False  # already logged without secrets
