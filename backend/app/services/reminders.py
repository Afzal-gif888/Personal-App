import uuid
from datetime import datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutils import as_utc, to_local, to_utc, utcnow
from app.models import Reminder, User
from app.models.enums import ReminderStatus, RepeatRule
from app.repositories.base import apply_patch, get_owned
from app.schemas.planning import ReminderIn, ReminderUpdate
from app.services.recurrence import advance


def list_reminders(
    db: Session, user: User, *, status: list[ReminderStatus] | None = None, limit: int = 500
) -> list[Reminder]:
    stmt = select(Reminder).where(Reminder.user_id == user.id)
    if status:
        stmt = stmt.where(Reminder.status.in_(status))
    return list(db.scalars(stmt.order_by(Reminder.scheduled_at).limit(limit)))


def get_reminder(db: Session, user: User, reminder_id: uuid.UUID) -> Reminder:
    return get_owned(db, Reminder, reminder_id, user.id, label="Reminder")


def create_reminder(db: Session, user: User, tz: ZoneInfo, data: ReminderIn, *, commit: bool = True) -> Reminder:
    values = data.model_dump(exclude={"date", "time"})
    values["scheduled_at"] = to_utc(data.scheduled_at, tz)
    reminder = Reminder(user_id=user.id, **values)
    db.add(reminder)
    db.flush()
    if commit:
        db.commit()
    return reminder


def update_reminder(db: Session, user: User, tz: ZoneInfo, reminder_id: uuid.UUID, data: ReminderUpdate) -> Reminder:
    reminder = get_reminder(db, user, reminder_id)
    patch = data.model_dump(exclude_unset=True)
    day, at = patch.pop("date", None), patch.pop("time", None)
    if "scheduled_at" not in patch and (day or at):
        current = to_local(as_utc(reminder.scheduled_at), tz)
        patch["scheduled_at"] = datetime.combine(day or current.date(), at or current.time())
    if "scheduled_at" in patch:
        patch["scheduled_at"] = to_utc(patch["scheduled_at"], tz)
        reminder.last_notified_at = None  # rescheduled: notify again
    apply_patch(reminder, patch, required=("title", "category", "scheduled_at", "repeat_rule", "status"))
    reminder.completed_at = utcnow() if reminder.status == ReminderStatus.COMPLETED else None
    db.commit()
    return reminder


def complete_reminder(db: Session, user: User, reminder_id: uuid.UUID) -> Reminder:
    """One-off reminders are completed; repeating ones roll forward to their next future occurrence."""
    reminder = get_reminder(db, user, reminder_id)
    reminder.completed_at = utcnow()
    if reminder.repeat_rule == RepeatRule.NONE:
        reminder.status = ReminderStatus.COMPLETED
    else:
        nxt = as_utc(reminder.scheduled_at)
        now = utcnow()
        while nxt <= now:
            nxt = cast(datetime, advance(nxt, reminder.repeat_rule))  # repeating rule: never None
        reminder.scheduled_at = nxt
        reminder.status = ReminderStatus.PENDING
        reminder.last_notified_at = None
    db.commit()
    return reminder


def snooze_reminder(db: Session, user: User, reminder_id: uuid.UUID, minutes: int) -> Reminder:
    reminder = get_reminder(db, user, reminder_id)
    reminder.scheduled_at = max(utcnow(), as_utc(reminder.scheduled_at)) + timedelta(minutes=minutes)
    reminder.status = ReminderStatus.SNOOZED
    reminder.last_notified_at = None
    db.commit()
    return reminder


def delete_reminder(db: Session, user: User, reminder_id: uuid.UUID) -> None:
    db.delete(get_reminder(db, user, reminder_id))
    db.commit()
