import logging

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import DB, client_ip
from app.core.rate_limit import rate_limit
from app.schemas.auth import (
    ForgotPasswordIn,
    LoginIn,
    LoginOtpOut,
    OtpTokenOut,
    RefreshIn,
    RegisterIn,
    RegisterOut,
    OtpMessage,
    ResendOtpIn,
    ResetPasswordIn,
    TokenOut,
    VerifyOtpIn,
)
from app.schemas.common import Message
from app.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(rate_limit("auth", "rate_limit_auth_per_minute"))])


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: DB, request: Request):
    return auth_service.register(db, data, ip=client_ip(request), user_agent=request.headers.get("user-agent"))


@router.post("/login", response_model=LoginOtpOut)
def login(data: LoginIn, db: DB, request: Request):
    """Step 1: email + password. Emails a 6-digit code; no token until /verify-otp."""
    return auth_service.login(db, data, ip=client_ip(request), user_agent=request.headers.get("user-agent"))


@router.post("/verify-otp", response_model=OtpTokenOut)
def verify_otp(data: VerifyOtpIn, db: DB, request: Request):
    """Step 2: the emailed code. Issues the session tokens."""
    return auth_service.verify_otp(db, data.email, data.otp, ip=client_ip(request),
                                   user_agent=request.headers.get("user-agent"))


@router.post("/resend-otp", response_model=OtpMessage)
def resend_otp(data: ResendOtpIn, db: DB):
    # Same response whether or not a sign-in is pending for that address.
    auth_service.resend_otp(db, data.email)
    return OtpMessage(message="A new OTP has been sent.")


@router.post("/refresh", response_model=TokenOut)
def refresh(data: RefreshIn, db: DB, request: Request):
    return auth_service.refresh(db, data.refresh_token, user_agent=request.headers.get("user-agent"))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshIn, db: DB):
    auth_service.logout(db, data.refresh_token)


@router.post("/forgot-password", response_model=Message, status_code=status.HTTP_202_ACCEPTED)
def forgot_password(data: ForgotPasswordIn, db: DB):
    # Identical response for known and unknown addresses, so it can't be used to discover accounts.
    auth_service.request_password_reset(db, data.email)
    return Message(message="If an account exists for that email, a reset link has been sent.")


@router.post("/reset-password", response_model=Message)
def reset_password(data: ResetPasswordIn, db: DB, request: Request):
    """Set a new password with the emailed link's token. Signs out every existing session."""
    auth_service.reset_password(db, data.token, data.new_password, ip=client_ip(request))
    return Message(message="Your password has been changed. Sign in with the new password.")
