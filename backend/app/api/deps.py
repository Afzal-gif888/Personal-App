import uuid
from dataclasses import dataclass
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError
from app.core.security import decode_access_token
from app.core.timeutils import get_zone
from app.db.session import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    if credentials is None:
        raise AuthenticationError("Authentication required")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise AuthenticationError("Invalid token", code="INVALID_TOKEN")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid token", code="INVALID_TOKEN")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_access_token(
    _user: CurrentUser, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> str:
    """The caller's own (already validated) access token, forwarded to the Agent Core."""
    assert credentials is not None  # get_current_user rejected the request otherwise
    return credentials.credentials


AccessToken = Annotated[str, Depends(get_access_token)]


def get_user_zone(user: CurrentUser) -> ZoneInfo:
    return get_zone(user.preferences.timezone if user.preferences else None)


UserZone = Annotated[ZoneInfo, Depends(get_user_zone)]


@dataclass
class Pagination:
    page: int
    page_size: int


def pagination(
    page: Annotated[int, Query(ge=1)] = 1, page_size: Annotated[int, Query(ge=1, le=100)] = 50
) -> Pagination:
    return Pagination(page, page_size)


Paging = Annotated[Pagination, Depends(pagination)]


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
