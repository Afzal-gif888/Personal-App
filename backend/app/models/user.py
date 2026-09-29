import uuid
from datetime import datetime, time

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAt, Timestamps, UserOwned, UUIDPk


class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    university: Mapped[str | None] = mapped_column(String(200))
    major: Mapped[str | None] = mapped_column(String(200))
    academic_year: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    preferences: Mapped["UserPreference"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )


class LoginOtp(UUIDPk, CreatedAt, Base):
    """Pending sign-in: the password was right, the emailed 6-digit code hasn't been entered yet.

    One row per user; a new login or resend replaces the code. Only a keyed hash of the code is
    stored, and the row is deleted when the code is used.
    """

    __tablename__ = "login_otps"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    otp_hash: Mapped[str | None] = mapped_column(String(64))  # None once too many wrong codes
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    send_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    window_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # resend allowed until


class RefreshToken(UUIDPk, CreatedAt, UserOwned, Base):
    """Server-side record of issued refresh tokens, enabling rotation and logout."""

    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(255))


class UserPreference(UUIDPk, Timestamps, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    daily_study_goal_minutes: Mapped[int] = mapped_column(Integer, default=120, server_default="120")
    preferred_study_start: Mapped[time | None] = mapped_column(Time)
    preferred_study_end: Mapped[time | None] = mapped_column(Time)
    default_reminder_time: Mapped[time] = mapped_column(Time, default=time(9, 0), server_default="09:00:00")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    notification_preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="preferences")
