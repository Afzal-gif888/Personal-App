from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timeutils import as_utc, local_today, to_local
from app.models import Approval, Notification, Task, User
from app.models.enums import ApprovalStatus, GoalStatus, StudySessionStatus, TaskStatus
from app.schemas.finance import BillOut
from app.schemas.planning import GoalOut, TaskOut
from app.schemas.platform import ApprovalOut, DashboardOut, DashboardStats, ScheduleItem
from app.services import approvals, events, finance, goals, study

OPEN_TASK = (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)


def summary(db: Session, user: User, tz: ZoneInfo) -> DashboardOut:
    today = local_today(tz)
    week_end = today + timedelta(days=6)
    approvals.expire_due(db, user_id=user.id)
    if finance.refresh_bill_statuses(db, user, tz):
        db.commit()

    def count(stmt) -> int:
        return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    open_tasks = select(Task.id).where(Task.user_id == user.id, Task.status.in_(OPEN_TASK))
    sessions = study.list_sessions(db, user, start=today, end=week_end)
    todays_minutes = sum(
        (datetime.combine(s.date, s.end_time) - datetime.combine(s.date, s.start_time)).seconds // 60
        for s in sessions
        if s.date == today and s.status != StudySessionStatus.CANCELLED
    )
    open_bills = finance.list_bills(db, user, tz, status=list(finance.OPEN_BILL_STATUSES), due_to=today + timedelta(days=30))
    currency = user.preferences.currency if user.preferences else "INR"
    month = finance.expense_summary(db, user, tz, None)

    stats = DashboardStats(
        tasks_due_today=count(open_tasks.where(Task.due_date == today)),
        overdue_tasks=count(open_tasks.where(Task.due_date < today)),
        open_tasks=count(open_tasks),
        pending_approvals=count(
            select(Approval.id).where(Approval.user_id == user.id, Approval.status == ApprovalStatus.PENDING)
        ),
        unread_notifications=count(
            select(Notification.id).where(Notification.user_id == user.id, Notification.read_at.is_(None))
        ),
        study_minutes_today=todays_minutes,
        daily_study_goal_minutes=user.preferences.daily_study_goal_minutes if user.preferences else 120,
        upcoming_bills_total=sum((b.amount for b in open_bills if b.currency == currency), Decimal("0")),
        month_spend=month["total"],
        currency=currency,
    )

    due_soon = db.scalars(
        select(Task)
        .where(Task.user_id == user.id, Task.status.in_(OPEN_TASK), Task.due_date <= week_end)
        .order_by(Task.due_date, Task.due_time.asc().nulls_last())
        .limit(8)
    )

    schedule = [
        ScheduleItem(
            kind="event",
            id=e.id,
            title=e.title,
            date=to_local(as_utc(e.start_at), tz).date(),
            start_time=to_local(as_utc(e.start_at), tz).strftime("%H:%M"),
            end_time=to_local(as_utc(e.end_at), tz).strftime("%H:%M") if e.end_at else None,
        )
        for e in events.list_events(db, user, tz, start=today, end=week_end)
    ] + [
        ScheduleItem(
            kind="study_session",
            id=s.id,
            title=s.topic if not s.subject_name else f"{s.subject_name}: {s.topic}",
            date=s.date,
            start_time=s.start_time.strftime("%H:%M"),
            end_time=s.end_time.strftime("%H:%M"),
        )
        for s in sessions
        if s.status == StudySessionStatus.SCHEDULED
    ]
    schedule.sort(key=lambda item: (item.date, item.start_time))

    pending, _ = approvals.list_approvals(db, user, page=1, page_size=5, status=[ApprovalStatus.PENDING])
    return DashboardOut(
        stats=stats,
        tasks_due_soon=[TaskOut.from_model(t) for t in due_soon],
        schedule=schedule,
        pending_approvals=[ApprovalOut.from_model(a) for a in pending],
        upcoming_bills=[BillOut.model_validate(b) for b in open_bills[:5]],
        active_goals=[GoalOut.from_model(g) for g in goals.list_goals(db, user, status=GoalStatus.ACTIVE)[:5]],
    )
