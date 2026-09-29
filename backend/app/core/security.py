"""Password hashing and JWT helpers."""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.errors import AuthenticationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def hash_token(token: str) -> str:
    """Refresh tokens are stored hashed so a database leak cannot be replayed."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    settings = get_settings()
    ttl = timedelta(minutes=settings.access_token_ttl_minutes)
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "type": "access", "iat": now, "exp": now + ttl, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), int(ttl.total_seconds())


def create_refresh_token(user_id: uuid.UUID, jti: str) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.refresh_token_ttl_days)
    payload = {"sub": str(user_id), "type": "refresh", "iat": now, "exp": expires_at, "jti": jti}
    return jwt.encode(payload, settings.jwt_refresh_secret, algorithm=settings.jwt_algorithm), expires_at


def _decode(token: str, secret: str, expected_type: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired", code="TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token", code="INVALID_TOKEN")
    if payload.get("type") != expected_type or "sub" not in payload:
        raise AuthenticationError("Invalid token", code="INVALID_TOKEN")
    return payload


def decode_access_token(token: str) -> dict:
    return _decode(token, get_settings().jwt_secret, "access")


def decode_refresh_token(token: str) -> dict:
    return _decode(token, get_settings().jwt_refresh_secret, "refresh")


# Password-reset links carry a signed token bound to the current password hash, so it stops working
# once the password changes.
EMAIL_TOKEN_PURPOSES = ("reset_password",)


def _email_binding(user, purpose: str) -> str:
    return hash_token(user.password_hash)[:24]


def create_email_token(user, purpose: str, ttl: timedelta) -> str:
    assert purpose in EMAIL_TOKEN_PURPOSES
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "type": purpose, "bind": _email_binding(user, purpose), "iat": now, "exp": now + ttl}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=get_settings().jwt_algorithm)


def decode_email_token(token: str, purpose: str) -> dict:
    return _decode(token, get_settings().jwt_secret, purpose)


def email_token_matches(user, purpose: str, payload: dict) -> bool:
    return hmac.compare_digest(str(payload.get("bind", "")), _email_binding(user, purpose))


def generate_otp() -> str:
    """Cryptographically secure 6-digit code (leading zeros kept)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(user_id: uuid.UUID, otp: str) -> str:
    """Keyed hash: a leaked database alone can't be brute-forced back to codes (only 10^6 exist)."""
    key = get_settings().jwt_secret.encode()
    return hmac.new(key, f"login-otp:{user_id}:{otp}".encode(), hashlib.sha256).hexdigest()


def otp_matches(user_id: uuid.UUID, otp: str, otp_hash: str | None) -> bool:
    return bool(otp_hash) and hmac.compare_digest(hash_otp(user_id, otp), otp_hash or "")
