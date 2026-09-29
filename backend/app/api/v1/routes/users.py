from fastapi import APIRouter, status

from app.api.deps import DB, CurrentUser
from app.schemas.user import PasswordChangeIn, PreferencesOut, PreferencesUpdate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users/me", tags=["users"])


@router.get("", response_model=UserOut)
def get_me(user: CurrentUser):
    return user


@router.patch("", response_model=UserOut)
def update_me(data: UserUpdate, user: CurrentUser, db: DB):
    return user_service.update_profile(db, user, data)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: PasswordChangeIn, user: CurrentUser, db: DB):
    """Changes the password and signs out every session (all refresh tokens are revoked)."""
    user_service.change_password(db, user, data)


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: CurrentUser, db: DB):
    user_service.get_preferences(db, user)
    return user_service.preferences_out(user)


@router.patch("/preferences", response_model=PreferencesOut)
def update_preferences(data: PreferencesUpdate, user: CurrentUser, db: DB):
    return user_service.update_preferences(db, user, data)
