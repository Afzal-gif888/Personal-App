import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ValidationFailed
from app.core.timeutils import as_utc, local_today, to_local
from app.models import StudyPlan, StudySession, User
from app.models.enums import Priority, StudyPlanStatus, StudySessionStatus
from app.repositories.base import apply_patch, get_owned
from app.schemas.planning import (
    PlanSessionIn,
    StudyPlanGenerateIn,
    StudyPlanIn,
    StudyPlanUpdate,
    StudySessionIn,
    StudySessionUpdate,
)
from app.services import events as event_service
from app.services import subjects

DEFAULT_WINDOW = (time(18, 0), time(22, 0))
DEFAULT_TOPICS = ["Core concepts review", "Worked examples", "Practice problems", "Past papers", "Weak areas review"]
BREAK = timedelta(minutes=15)


# --- Plans ----------------------------------------------------------------------------------------


def list_plans(db: Session, user: User, *, status: StudyPlanStatus | None = None) -> list[StudyPlan]:
    stmt = select(StudyPlan).where(StudyPlan.user_id == user.id).options(selectinload(StudyPlan.sessions))
    if status:
        stmt = stmt.where(StudyPlan.status == status)
    return list(db.scalars(stmt.order_by(StudyPlan.created_at.desc())))


def get_plan(db: Session, user: User, plan_id: uuid.UUID) -> StudyPlan:
    return get_owned(db, StudyPlan, plan_id, user.id, label="Study plan")


def create_plan(db: Session, user: User, data: StudyPlanIn, *, commit: bool = True) -> StudyPlan:
    plan = StudyPlan(user_id=user.id, **data.model_dump(exclude={"sessions"}))
    for s in data.sessions:
        if s.end_time <= s.start_time:
            raise ValidationFailed("Session endTime must be after startTime")
        subject = subjects.resolve(db, user, None, s.subject_name)
        plan.sessions.append(
            StudySession(
                user_id=user.id,
                subject_id=subject.id if subject else None,
                **s.model_dump(),
            )
        )
    dates = [s.date for s in data.sessions]
    plan.start_date = plan.start_date or (min(dates) if dates else None)
    plan.end_date = plan.end_date or (max(dates) if dates else None)
    db.add(plan)
    db.flush()
    if commit:
        db.commit()
    return plan


def update_plan(db: Session, user: User, plan_id: uuid.UUID, data: StudyPlanUpdate) -> StudyPlan:
    plan = get_plan(db, user, plan_id)
    apply_patch(plan, data.model_dump(exclude_unset=True), required=("title", "status"))
    db.commit()
    return plan


def delete_plan(db: Session, user: User, plan_id: uuid.UUID) -> None:
    db.delete(get_plan(db, user, plan_id))
    db.commit()


# --- Sessions -------------------------------------------------------------------------------------


def list_sessions(
    db: Session,
    user: User,
    *,
    start: date | None = None,
    end: date | None = None,
    status: StudySessionStatus | None = None,
    plan_id: uuid.UUID | None = None,
) -> list[StudySession]:
    stmt = select(StudySession).where(StudySession.user_id == user.id)
    if start:
        stmt = stmt.where(StudySession.date >= start)
    if end:
        stmt = stmt.where(StudySession.date <= end)
    if status:
        stmt = stmt.where(StudySession.status == status)
    if plan_id:
        stmt = stmt.where(StudySession.study_plan_id == plan_id)
    return list(db.scalars(stmt.order_by(StudySession.date, StudySession.start_time)))


def get_session(db: Session, user: User, session_id: uuid.UUID) -> StudySession:
    return get_owned(db, StudySession, session_id, user.id, label="Study session")


def create_session(db: Session, user: User, data: StudySessionIn) -> StudySession:
    if data.study_plan_id:
        get_plan(db, user, data.study_plan_id)
    subject = subjects.resolve(db, user, data.subject_id, data.subject_name)
    session = StudySession(
        user_id=user.id, **data.model_dump(exclude={"subject_id"}), subject_id=subject.id if subject else None
    )
    db.add(session)
    db.commit()
    return session


def update_session(db: Session, user: User, session_id: uuid.UUID, data: StudySessionUpdate) -> StudySession:
    session = get_session(db, user, session_id)
    patch = data.model_dump(exclude_unset=True)
    if "subject_id" in patch:
        subject = subjects.resolve(db, user, patch.pop("subject_id"), None)
        session.subject_id = subject.id if subject else None
    apply_patch(session, patch, required=("topic", "date", "start_time", "end_time", "priority", "status"))
    if session.end_time <= session.start_time:
        raise ValidationFailed("endTime must be after startTime")
    db.commit()
    return session


def delete_session(db: Session, user: User, session_id: uuid.UUID) -> None:
    db.delete(get_session(db, user, session_id))
    db.commit()


# --- Planner --------------------------------------------------------------------------------------


def build_plan(db: Session, user: User, tz: ZoneInfo, spec: StudyPlanGenerateIn) -> StudyPlanIn:
    """Lay out sessions inside the user's study window, skipping slots taken by events or other sessions.

    Pure planning: nothing is persisted, so the result can be shown for approval first.
    """
    prefs = user.preferences
    window_start = (prefs.preferred_study_start if prefs else None) or DEFAULT_WINDOW[0]
    window_end = (prefs.preferred_study_end if prefs else None) or DEFAULT_WINDOW[1]
    if window_end <= window_start:
        window_start, window_end = DEFAULT_WINDOW

    start = spec.start_date or local_today(tz) + timedelta(days=1)
    end = start + timedelta(days=spec.days - 1)
    busy = busy_intervals(db, user, tz, start, end)
    topics = spec.topics or DEFAULT_TOPICS
    session_len = timedelta(minutes=spec.session_minutes)

    sessions: list[PlanSessionIn] = []
    for offset in range(spec.days):
        day = start + timedelta(days=offset)
        remaining = timedelta(minutes=spec.minutes_per_day)
        for slot_start, slot_end in free_slots(day, window_start, window_end, busy.get(day, [])):
            cursor = slot_start
            while remaining >= timedelta(minutes=15) and cursor + min(session_len, remaining) <= slot_end:
                length = min(session_len, remaining)
                topic = topics[len(sessions) % len(topics)]
                sessions.append(
                    PlanSessionIn(
                        topic=topic,
                        subject_name=spec.subject,
                        date=day,
                        start_time=cursor.time(),
                        end_time=(cursor + length).time(),
                        # Front-load effort: the first half of the plan is high priority.
                        priority=Priority.HIGH if offset < max(1, spec.days // 2) else Priority.MEDIUM,
                    )
                )
                remaining -= length
                cursor += length + BREAK
    if not sessions:
        raise ValidationFailed("No free time found in your study window for these dates")
    total = sum(
        (datetime.combine(s.date, s.end_time) - datetime.combine(s.date, s.start_time)).seconds for s in sessions
    )
    return StudyPlanIn(
        title=f"{spec.subject} study plan",
        description=f"{len(sessions)} sessions, {total / 3600:.1f} hours between {start:%b %d} and {end:%b %d}.",
        start_date=start,
        end_date=end,
        status=StudyPlanStatus.ACTIVE,
        sessions=sessions,
    )


def busy_intervals(
    db: Session, user: User, tz: ZoneInfo, start: date, end: date
) -> dict[date, list[tuple[datetime, datetime]]]:
    """Naive local-time intervals per day that are already taken."""
    busy: dict[date, list[tuple[datetime, datetime]]] = {}
    for ev in event_service.list_events(db, user, tz, start=start, end=end):
        s = to_local(as_utc(ev.start_at), tz).replace(tzinfo=None)
        e = to_local(as_utc(ev.end_at), tz).replace(tzinfo=None) if ev.end_at else s + timedelta(hours=1)
        busy.setdefault(s.date(), []).append((s, e))
    for sess in list_sessions(db, user, start=start, end=end):
        if sess.status in (StudySessionStatus.CANCELLED, StudySessionStatus.MISSED):
            continue
        busy.setdefault(sess.date, []).append(
            (datetime.combine(sess.date, sess.start_time), datetime.combine(sess.date, sess.end_time))
        )
    return busy


def free_slots(
    day: date, window_start: time, window_end: time, busy: list[tuple[datetime, datetime]]
) -> list[tuple[datetime, datetime]]:
    cursor, stop = datetime.combine(day, window_start), datetime.combine(day, window_end)
    slots = []
    for b_start, b_end in sorted(busy):
        if b_end <= cursor or b_start >= stop:
            continue
        if b_start > cursor:
            slots.append((cursor, b_start))
        cursor = max(cursor, b_end)
    if cursor < stop:
        slots.append((cursor, stop))
    return slots
