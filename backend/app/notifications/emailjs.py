"""Email delivery through EmailJS (server-side REST API).

    POST https://api.emailjs.com/api/v1.0/email/send
    {service_id, template_id, user_id: <public key>, accessToken: <private key>, template_params}

Every template receives `to_email`, `email` and `name`; set the template's "To Email" field to
{{to_email}} in the EmailJS dashboard. Credentials come only from EMAILJS_* settings and are never
logged; failures are logged with the HTTP status only (template parameters can contain an OTP).
"""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

API_URL = "https://api.emailjs.com/api/v1.0/email/send"


class EmailError(Exception):
    pass


def emailjs_configured(template_id: str | None = None) -> bool:
    s = get_settings()
    return bool(s.emailjs_service_id and s.emailjs_public_key and s.emailjs_private_key and (template_id or s.emailjs_template_id))


def _post(body: dict[str, Any]) -> httpx.Response:
    return httpx.post(API_URL, json=body, timeout=get_settings().emailjs_timeout_seconds)


def send_template(template_id: str, to_email: str, name: str, params: dict[str, Any]) -> None:
    """Send one email through an EmailJS template. Raises EmailError on any failure."""
    s = get_settings()
    if not emailjs_configured(template_id) or not template_id:
        raise EmailError("EmailJS is not configured")
    body = {
        "service_id": s.emailjs_service_id,
        "template_id": template_id,
        "user_id": s.emailjs_public_key,
        "accessToken": s.emailjs_private_key,
        "template_params": {"to_email": to_email, "email": to_email, "name": name, **params},
    }
    try:
        resp = _post(body)
    except httpx.HTTPError as exc:
        logger.warning("EmailJS unreachable", extra={"error": type(exc).__name__})
        raise EmailError("EmailJS unreachable") from exc
    if resp.status_code != 200:
        # 403 usually means "API access from non-browser applications" is off in EmailJS
        # Account > Security; 400 a wrong service/template id or key.
        logger.warning("EmailJS rejected the email", extra={"status": resp.status_code})
        raise EmailError(f"EmailJS returned {resp.status_code}")
