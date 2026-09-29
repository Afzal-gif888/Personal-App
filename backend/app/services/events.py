import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.core.timeutils import as_utc, local_day_bounds, to_local, to_utc
from app.models import Event, User
from app.models.enums import EventType
from app.repositories.base import apply_patch, get_owned
from app.schemas.planning import EventIn, EventUpdate


def list_events(
    db: Session,
    user: User,
    tz: ZoneInfo,
    *,
    start: date | None = None,
    end: date | None = None,
    event_type: EventType | None = None,
    limit: int = 500,
) -> list[Event]:
    stmt = select(Event).where(Event.user_id == user.id)
    if start:
        stmt = stmt.where(Event.start_at >= local_day_bounds(start, tz)[0])
    if end:
        stmt = stmt.where(Event.start_at <= local_day_bounds(end, tz)[1])
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    return list(db.scalars(stmt.order_by(Event.start_at).limit(limit)))


def get_event(db: Session, user: User, event_id: uuid.UUID) -> Event:
    return get_owned(db, Event, event_id, user.id, label="Event")


def create_event(db: Session, user: User, tz: ZoneInfo, data: EventIn, *, commit: bool = True) -> Event:
    values = data.model_dump(exclude={"date", "start_time", "end_time"})
    start_at, end_at = to_utc(data.start_at, tz), to_utc(data.end_at, tz)
    assert start_at is not None  # EventIn._resolve rejects input without a start
    _check_range(start_at, end_at)
    values["start_at"], values["end_at"] = start_at, end_at
    event = Event(user_id=user.id, **values)
    db.add(event)
    db.flush()
    if commit:
        db.commit()
    return event


def update_event(db: Session, user: User, tz: ZoneInfo, event_id: uuid.UUID, data: EventUpdate) -> Event:
    event = get_event(db, user, event_id)
    patch = data.model_dump(exclude_unset=True)
    old_start, old_end = as_utc(event.start_at), as_utc(event.end_at)
    local_start = to_local(old_start, tz)

    # Local edits (date / startTime / endTime) are merged into the existing value, not required in full.
    day = patch.pop("date", None)
    start_time = patch.pop("start_time", None)
    end_time = patch.pop("end_time", None)
    if "start_at" not in patch and (day or start_time):
        patch["start_at"] = datetime.combine(day or local_start.date(), start_time or local_start.time())
    for key in ("start_at", "end_at"):
        if patch.get(key) is not None:
            patch[key] = to_utc(patch[key], tz)
    if "end_at" not in patch:
        new_start = patch.get("start_at", old_start)
        if end_time:
            patch["end_at"] = to_utc(datetime.combine(to_local(new_start, tz).date(), end_time), tz)
        elif old_end and "start_at" in patch:
            patch["end_at"] = new_start + (old_end - old_start)  # moving an event keeps its duration

    apply_patch(event, patch, required=("title", "event_type", "start_at"))
    _check_range(as_utc(event.start_at), as_utc(event.end_at))
    db.commit()
    return event


def delete_event(db: Session, user: User, event_id: uuid.UUID) -> None:
    db.delete(get_event(db, user, event_id))
    db.commit()


def _check_range(start: datetime, end: datetime | None) -> None:
    if end is not None and end <= start:
        raise ValidationFailed("endAt must be after startAt")
    if end is not None and end - start > timedelta(days=31):
        raise ValidationFailed("Events cannot span more than 31 days")
