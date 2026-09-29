"""Timezone helpers. All timestamps are stored in UTC and converted per user at the edges."""

from datetime import date, datetime, time, timezone
from typing import overload
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.errors import ValidationFailed


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@overload
def as_utc(value: datetime) -> datetime: ...
@overload
def as_utc(value: None) -> None: ...
@overload
def as_utc(value: datetime | None) -> datetime | None: ...
def as_utc(value: datetime | None) -> datetime | None:
    """Normalise a stored timestamp to aware UTC (SQLite hands back naive values)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_zone(tz_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def validate_timezone(tz_name: str) -> str:
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValidationFailed(f"Unknown timezone: {tz_name}")
    return tz_name


@overload
def to_utc(value: datetime, tz: ZoneInfo) -> datetime: ...
@overload
def to_utc(value: None, tz: ZoneInfo) -> None: ...
@overload
def to_utc(value: datetime | None, tz: ZoneInfo) -> datetime | None: ...
def to_utc(value: datetime | None, tz: ZoneInfo) -> datetime | None:
    """Naive datetimes from the client are interpreted in the user's timezone."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz)
    return value.astimezone(timezone.utc)


@overload
def to_local(value: datetime, tz: ZoneInfo) -> datetime: ...
@overload
def to_local(value: None, tz: ZoneInfo) -> None: ...
@overload
def to_local(value: datetime | None, tz: ZoneInfo) -> datetime | None: ...
def to_local(value: datetime | None, tz: ZoneInfo) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz)


def local_today(tz: ZoneInfo) -> date:
    return utcnow().astimezone(tz).date()


def local_day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """UTC [start, end) for a calendar day in the user's timezone."""
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = datetime.combine(day, time.max, tzinfo=tz)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)
