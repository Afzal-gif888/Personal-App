import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, ConflictError, EmailDeliveryError, OtpError, RateLimited
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_email_token,
    decode_refresh_token,
    email_token_matches,
    generate_otp,
    hash_otp,
    hash_password,
    hash_token,
    otp_matches,
    verify_password,
)
from app.core.timeutils import as_utc, utcnow, validate_timezone
from app.models import LoginOtp, RefreshToken, User, UserPreference
from app.notifications.emailjs import EmailError
from app.schemas.auth import LoginIn, LoginOtpOut, OtpTokenOut, RegisterIn, RegisterOut, TokenOut
from app.schemas.user import NOTIFICATION_DEFAULTS, UserOut
from app.services import account_emails, audit

# Verified against when the email is unknown, so response time doesn't reveal which emails exist.
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")

# Login OTP policy.
OTP_TTL = timedelta(minutes=5)
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN = timedelta(seconds=30)
OTP_MAX_SENDS = 5  # codes per pending sign-in (login + resends) ...
OTP_WINDOW = timedelta(minutes=15)  # ... within this window


def _issue_tokens(db: Session, user: User, user_agent: str | None) -> TokenOut:
    access, expires_in = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id, uuid.uuid4().hex)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    return TokenOut(
        access_token=access, refresh_token=refresh_token, expires_in=expires_in, user=UserOut.model_validate(user)
    )


def register(db: Session, data: RegisterIn, *, ip: str | None, user_agent: str | None) -> RegisterOut:
    """Create the account. No email and no session: the user signs in (password + emailed code) next."""
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise ConflictError("An account with this email already exists", code="EMAIL_TAKEN")
    user = User(name=data.name, email=email, password_hash=hash_password(data.password))
    user.preferences = UserPreference(
        timezone=validate_timezone(data.timezone) if data.timezone else "UTC",
        notification_preferences=dict(NOTIFICATION_DEFAULTS),
    )
    db.add(user)
    db.flush()
    audit.record(db, "auth.register", user_id=user.id, resource_type="user", resource_id=user.id, ip_address=ip)
    db.commit()
    return RegisterOut(user=UserOut.model_validate(user), message="Account created. Sign in to continue.")


# --- sign-in: password, then a one-time code sent by email -----------------------------------------


def login(db: Session, data: LoginIn, *, ip: str | None, user_agent: str | None) -> LoginOtpOut:
    """Step 1: check the password and email a one-time code. No token is issued here."""
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None:
        verify_password(data.password, _DUMMY_HASH)
        raise AuthenticationError("Invalid email or password", code="INVALID_CREDENTIALS")
    if not verify_password(data.password, user.password_hash) or not user.is_active:
        audit.record(db, "auth.login_failed", user_id=user.id, ip_address=ip)
        db.commit()
        raise AuthenticationError("Invalid email or password", code="INVALID_CREDENTIALS")
    now = utcnow()
    pending = db.scalar(select(LoginOtp).where(LoginOtp.user_id == user.id))
    if pending is not None and as_utc(pending.window_expires_at) > now:
        _check_send_allowed(pending, now)
    elif pending is not None:
        db.delete(pending)  # the old sign-in window is over: start afresh
        db.flush()
        pending = None
    _send_new_otp(db, user, pending, now)
    audit.record(db, "auth.login_otp_sent", user_id=user.id, ip_address=ip)
    db.commit()
    return LoginOtpOut(message="OTP sent to your email.", email=user.email)


def _check_send_allowed(pending: LoginOtp, now: datetime) -> None:
    wait = (OTP_RESEND_COOLDOWN - (now - as_utc(pending.sent_at))).total_seconds()
    if wait > 0:
        raise RateLimited(f"Please wait {int(wait) + 1} seconds before requesting another code.",
                          code="OTP_RESEND_COOLDOWN", details={"retryAfter": int(wait) + 1})
    if pending.send_count >= OTP_MAX_SENDS:
        retry = int((as_utc(pending.window_expires_at) - now).total_seconds()) + 1
        raise RateLimited("Too many codes requested. Please try again later.",
                          code="OTP_SEND_LIMIT", details={"retryAfter": retry})


def _send_new_otp(db: Session, user: User, pending: LoginOtp | None, now: datetime) -> None:
    """Replace any earlier code with a new one (only its hash is stored) and email it."""
    otp = generate_otp()
    if pending is None:
        pending = LoginOtp(user_id=user.id, send_count=0, window_expires_at=now + OTP_WINDOW)
        db.add(pending)
    pending.otp_hash = hash_otp(user.id, otp)  # the previous code stops working
    pending.expires_at = now + OTP_TTL
    pending.attempts = 0
    pending.sent_at = now
    pending.send_count += 1
    db.flush()
    try:
        account_emails.send_login_otp(user, otp)
    except EmailError as exc:
        db.rollback()
        raise EmailDeliveryError("We couldn't send the verification code. Please try again shortly.") from exc


def verify_otp(db: Session, email: str, otp: str, *, ip: str | None, user_agent: str | None) -> OtpTokenOut:
    """Step 2: the emailed code. Only a correct, unexpired, unused code issues the session."""
    user = db.scalar(select(User).where(User.email == email.lower()))
    pending = db.scalar(select(LoginOtp).where(LoginOtp.user_id == user.id)) if user is not None else None
    if user is None or pending is None or not user.is_active:
        raise OtpError("Invalid or expired code. Sign in again to get a new one.")
    if pending.otp_hash is None:
        raise OtpError("Too many incorrect attempts. Sign in again to get a new code.", code="OTP_TOO_MANY_ATTEMPTS")
    if as_utc(pending.expires_at) <= utcnow():
        raise OtpError("This code has expired. Request a new one.", code="OTP_EXPIRED")
    if not otp_matches(user.id, otp, pending.otp_hash):
        pending.attempts += 1
        remaining = OTP_MAX_ATTEMPTS - pending.attempts
        if remaining <= 0:
            pending.otp_hash = None  # locked: only a new sign-in can issue another code
        audit.record(db, "auth.otp_failed", user_id=user.id, ip_address=ip)
        db.commit()
        if remaining <= 0:
            raise OtpError("Too many incorrect attempts. Sign in again to get a new code.", code="OTP_TOO_MANY_ATTEMPTS")
        raise OtpError(f"Incorrect code. {remaining} attempt{'s' if remaining != 1 else ''} left.",
                       details={"attemptsLeft": remaining})
    # Single use: only the request that deletes the row gets a session, even under concurrency.
    used = db.execute(delete(LoginOtp).where(LoginOtp.id == pending.id, LoginOtp.otp_hash == pending.otp_hash))
    if getattr(used, "rowcount", 0) != 1:
        db.rollback()
        raise OtpError("Invalid or expired code. Sign in again to get a new one.")
    user.last_login_at = utcnow()
    tokens = _issue_tokens(db, user, user_agent)
    audit.record(db, "auth.login", user_id=user.id, ip_address=ip)
    db.commit()
    return OtpTokenOut(**tokens.model_dump(), token=tokens.access_token)


def resend_otp(db: Session, email: str) -> None:
    """New code for a sign-in in progress; the old code stops working. Does nothing when no sign-in
    is pending, so the endpoint can't be used to email arbitrary addresses."""
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        return
    now = utcnow()
    pending = db.scalar(select(LoginOtp).where(LoginOtp.user_id == user.id))
    if pending is None or as_utc(pending.window_expires_at) <= now:
        return
    _check_send_allowed(pending, now)
    _send_new_otp(db, user, pending, now)
    audit.record(db, "auth.login_otp_resent", user_id=user.id)
    db.commit()


# --- sessions --------------------------------------------------------------------------------------


def refresh(db: Session, token: str, *, user_agent: str | None) -> TokenOut:
    payload = decode_refresh_token(token)
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if record is None or str(record.user_id) != payload["sub"]:
        raise AuthenticationError("Invalid refresh token", code="INVALID_TOKEN")
    if record.revoked_at is not None:
        # A rotated token was replayed: assume theft and end every session for this user.
        revoke_all(db, record.user_id)
        audit.record(db, "auth.refresh_reuse_detected", user_id=record.user_id)
        db.commit()
        raise AuthenticationError("Refresh token has been revoked", code="TOKEN_REVOKED")
    if as_utc(record.expires_at) <= utcnow():
        raise AuthenticationError("Refresh token has expired", code="TOKEN_EXPIRED")
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid refresh token", code="INVALID_TOKEN")
    record.revoked_at = utcnow()
    tokens = _issue_tokens(db, user, user_agent)
    db.commit()
    return tokens


def logout(db: Session, token: str) -> None:
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if record is not None and record.revoked_at is None:
        record.revoked_at = utcnow()
        audit.record(db, "auth.logout", user_id=record.user_id)
        db.commit()


def revoke_all(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


# --- password reset --------------------------------------------------------------------------------


def _user_for_token(db: Session, token: str, purpose: str) -> User:
    payload = decode_email_token(token, purpose)
    try:
        user = db.get(User, uuid.UUID(payload["sub"]))
    except ValueError:
        user = None
    if user is None or not user.is_active or not email_token_matches(user, purpose, payload):
        # Used already (password changed / email changed) or for an account that no longer exists.
        raise AuthenticationError("This link is no longer valid. Request a new one.", code="INVALID_TOKEN")
    return user


def request_password_reset(db: Session, email: str) -> None:
    """Emails a reset link if the account exists. Callers respond identically either way."""
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        return
    account_emails.send_password_reset_email(user)
    audit.record(db, "auth.password_reset_requested", user_id=user.id, resource_type="user", resource_id=user.id)
    db.commit()


def reset_password(db: Session, token: str, new_password: str, *, ip: str | None = None) -> None:
    user = _user_for_token(db, token, "reset_password")
    user.password_hash = hash_password(new_password)  # also invalidates this and any other reset link
    revoke_all(db, user.id)  # sign out every session
    audit.record(db, "auth.password_reset", user_id=user.id, resource_type="user", resource_id=user.id, ip_address=ip)
    db.commit()
