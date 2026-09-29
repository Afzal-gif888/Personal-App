import uuid
from datetime import time

from pydantic import Field, field_validator

from app.core.timeutils import validate_timezone
from app.schemas.common import HHMM, APIModel, Currency, InputModel, UTCDateTime

# Stored camelCase in the JSON column so it round-trips to the frontend's NotificationSettings unchanged.
NOTIFICATION_DEFAULTS = {
    "reminders": True,
    "studyNotifications": True,
    "aiNotifications": True,
    "emailNotifications": True,  # reminders reach students by email unless they turn it off
}


class UserOut(APIModel):
    id: uuid.UUID
    name: str
    email: str
    avatar_url: str | None
    university: str | None
    major: str | None
    academic_year: str | None
    bio: str | None
    created_at: UTCDateTime


class UserUpdate(InputModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=1024)
    university: str | None = Field(default=None, max_length=200)
    major: str | None = Field(default=None, max_length=200)
    academic_year: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=2000)


class PasswordChangeIn(InputModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class NotificationPreferences(InputModel):
    reminders: bool = True
    study_notifications: bool = True
    ai_notifications: bool = True
    email_notifications: bool = False


class PreferencesOut(APIModel):
    daily_study_goal_minutes: int
    preferred_study_start: HHMM | None
    preferred_study_end: HHMM | None
    default_reminder_time: HHMM
    timezone: str
    currency: str
    notification_preferences: NotificationPreferences


class PreferencesUpdate(InputModel):
    daily_study_goal_minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    preferred_study_start: time | None = None
    preferred_study_end: time | None = None
    default_reminder_time: time | None = None
    timezone: str | None = Field(default=None, max_length=64)
    currency: Currency | None = None
    notification_preferences: NotificationPreferences | None = None

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str | None) -> str | None:
        return validate_timezone(value) if value else value
