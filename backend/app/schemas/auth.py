from pydantic import EmailStr, Field

from app.schemas.common import APIModel, InputModel
from app.schemas.user import UserOut


class RegisterIn(InputModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    timezone: str | None = Field(default=None, max_length=64)


class LoginIn(InputModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(InputModel):
    refresh_token: str = Field(min_length=1)


class ForgotPasswordIn(InputModel):
    email: EmailStr


class TokenOut(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ResetPasswordIn(InputModel):
    token: str = Field(min_length=10, max_length=2000)
    new_password: str = Field(min_length=8, max_length=128)


class RegisterOut(APIModel):
    """Registration doesn't sign the user in: they sign in (password + emailed code) next."""

    user: UserOut
    message: str


class LoginOtpOut(APIModel):
    """Step 1 of sign-in: the password was right and a code was emailed. No session yet."""

    success: bool = True
    requires_otp: bool = True
    message: str
    email: str


class VerifyOtpIn(InputModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")


class ResendOtpIn(InputModel):
    email: EmailStr


class OtpTokenOut(TokenOut):
    """Step 2: the code was right. The normal session tokens, plus `token` (= access token)."""

    success: bool = True
    message: str = "Login successful"
    token: str


class OtpMessage(APIModel):
    success: bool = True
    message: str
