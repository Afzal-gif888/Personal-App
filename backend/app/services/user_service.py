from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError
from app.core.security import hash_password, verify_password
from app.models import User, UserPreference
from app.repositories.base import apply_patch
from app.schemas.user import (
    NOTIFICATION_DEFAULTS,
    NotificationPreferences,
    PasswordChangeIn,
    PreferencesOut,
    PreferencesUpdate,
    UserUpdate,
)
from app.services import audit, auth_service


def get_preferences(db: Session, user: User) -> UserPreference:
    if user.preferences is None:
        user.preferences = UserPreference(notification_preferences=dict(NOTIFICATION_DEFAULTS))
        db.commit()
    return user.preferences


def notification_flags(user: User) -> dict:
    stored = user.preferences.notification_preferences if user.preferences else None
    return {**NOTIFICATION_DEFAULTS, **(stored or {})}


def preferences_out(user: User) -> PreferencesOut:
    prefs = user.preferences
    return PreferencesOut(
        daily_study_goal_minutes=prefs.daily_study_goal_minutes,
        preferred_study_start=prefs.preferred_study_start,
        preferred_study_end=prefs.preferred_study_end,
        default_reminder_time=prefs.default_reminder_time,
        timezone=prefs.timezone,
        currency=prefs.currency,
        notification_preferences=NotificationPreferences.model_validate(notification_flags(user)),
    )


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    apply_patch(user, data.model_dump(exclude_unset=True), required=("name",))
    db.commit()
    return user


def update_preferences(db: Session, user: User, data: PreferencesUpdate) -> PreferencesOut:
    prefs = get_preferences(db, user)
    patch = data.model_dump(exclude_unset=True)
    patch.pop("notification_preferences", None)
    apply_patch(prefs, patch, required=("daily_study_goal_minutes", "default_reminder_time", "timezone", "currency"))
    if data.notification_preferences is not None:
        # Reassign (not mutate) so SQLAlchemy notices the JSON change.
        prefs.notification_preferences = {
            **notification_flags(user),
            **data.notification_preferences.model_dump(by_alias=True),
        }
    db.commit()
    return preferences_out(user)


def change_password(db: Session, user: User, data: PasswordChangeIn) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise AuthenticationError("Current password is incorrect", code="INVALID_CREDENTIALS")
    user.password_hash = hash_password(data.new_password)
    auth_service.revoke_all(db, user.id)
    audit.record(db, "user.password_changed", user_id=user.id)
    db.commit()
