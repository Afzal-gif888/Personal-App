"""Periodic jobs: deliver due reminders, flag bills, warn about upcoming events, expire approvals.

Run in-process with SCHEDULER_ENABLED=true (one API instance only), or as a separate process with
`python -m scripts.run_scheduler`. Every job is idempotent: notifications carry a dedupe key, so
overlapping runs or several scheduler processes don't produce duplicates.
"""

import logging
import threading
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.timeutils import as_utc, get_zone, to_local, utcnow
from app.db.session import session_scope
from app.models import Bill, Event, Reminder, User
from app.models.enums import MEETING_EVENT_TYPES, BillStatus, NotificationType, ReminderStatus, TaskCategory
from app.notifications import notify, retry_failed_emails
from app.rag.indexing import index_pending
from app.services import approvals, finance

logger = logging.getLogger(__name__)

EVENT_LEAD_TIME = timedelta(minutes=30)
BATCH = 500

# How a reminder's category reads in the email.
REMINDER_TYPE_LABELS = {
    TaskCategory.ACADEMIC: "Study / academic",
    TaskCategory.FINANCIAL: "Payment / financial",
    TaskCategory.PERSONAL: "Personal",
    TaskCategory.CAREER: "Career",
    TaskCategory.GENERAL: "General",
}


def dispatch_due_reminders(db: Session, now: datetime) -> int:
    due = db.scalars(
        select(Reminder)
        .where(
            Reminder.status.in_([ReminderStatus.PENDING, ReminderStatus.SNOOZED]),
            Reminder.scheduled_at <= now,
            or_(Reminder.last_notified_at.is_(None), Reminder.last_notified_at < Reminder.scheduled_at),
        )
        .order_by(Reminder.scheduled_at)
        .limit(BATCH)
    ).all()
    sent = 0
    for reminder in due:
        user = db.get_one(User, reminder.user_id)
        at = as_utc(reminder.scheduled_at)
        local = to_local(at, get_zone(user.preferences.timezone if user.preferences else None))
        when = f"{local:%a %d %b, %H:%M}"
        # Shown line by line in the reminder email (and kept for retries).
        details = [["Reminder", reminder.title], ["Type", REMINDER_TYPE_LABELS.get(reminder.category, "General")],
                   ["When", when]]
        if reminder.description:
            details.append(["Notes", reminder.description])
        if notify(
            db, user, NotificationType.REMINDER, reminder.title,
            reminder.description or f"Reminder for {when}",
            dedupe_key=f"reminder:{reminder.id}:{at.isoformat()}", scheduled_at=at,
            meta={"reminderId": str(reminder.id), "details": details},
        ):
            sent += 1
        reminder.last_notified_at = now  # also when muted, so it isn't re-examined every tick
    return sent


def refresh_bills(db: Session) -> int:
    """Update bill statuses per user timezone and notify when a bill becomes due or overdue."""
    user_ids = db.scalars(
        select(Bill.user_id).where(Bill.status.in_(finance.OPEN_BILL_STATUSES)).distinct()
    ).all()
    sent = 0
    for user_id in user_ids:
        user = db.get_one(User, user_id)
        tz = get_zone(user.preferences.timezone if user.preferences else None)
        finance.refresh_bill_statuses(db, user, tz)
        db.flush()  # sessions don't autoflush; the query below must see the new statuses
        # Every due/overdue bill, not just ones that changed this tick: a bill can be created already
        # due. The dedupe key keeps it to one notification per bill per status.
        due_bills = db.scalars(
            select(Bill).where(Bill.user_id == user_id, Bill.status.in_([BillStatus.DUE, BillStatus.OVERDUE]))
        )
        for bill in due_bills:
            when = "is overdue" if bill.status == BillStatus.OVERDUE else f"is due on {bill.due_date:%d %b}"
            if notify(
                db, user, NotificationType.BILL, f"{bill.title} {when}",
                f"{bill.currency} {bill.amount:,.2f} {when}.",
                dedupe_key=f"bill:{bill.id}:{bill.status.value}:{bill.due_date.isoformat()}",
                meta={"billId": str(bill.id)},
            ):
                sent += 1
    return sent


def notify_upcoming_events(db: Session, now: datetime) -> int:
    upcoming = db.scalars(
        select(Event).where(Event.start_at > now, Event.start_at <= now + EVENT_LEAD_TIME).limit(BATCH)
    ).all()
    sent = 0
    for event in upcoming:
        user = db.get_one(User, event.user_id)
        start = as_utc(event.start_at)
        local = to_local(start, get_zone(user.preferences.timezone if user.preferences else None))
        type_ = NotificationType.MEETING if event.event_type in MEETING_EVENT_TYPES else NotificationType.EVENT
        if notify(
            db, user, type_, f"Starting soon: {event.title}",
            f"Starts at {local:%H:%M}" + (f" · {event.location}" if event.location else ""),
            dedupe_key=f"event:{event.id}:{start.isoformat()}", meta={"eventId": str(event.id)},
        ):
            sent += 1
    return sent


def run_once() -> dict[str, int]:
    """One scheduler tick. Each job commits on its own so one failure doesn't block the others."""
    results: dict[str, int] = {}
    jobs = {
        "reminders": lambda db: dispatch_due_reminders(db, utcnow()),
        "bills": refresh_bills,
        "events": lambda db: notify_upcoming_events(db, utcnow()),
        "approvals_expired": lambda db: approvals.expire_due(db),
        "emails_retried": retry_failed_emails,
        "documents_indexed": index_pending,
    }
    for name, job in jobs.items():
        try:
            with session_scope() as db:
                results[name] = job(db)
        except Exception:
            logger.exception("Scheduler job failed", extra={"job": name})
            results[name] = -1
    return results


class Scheduler:
    """Background thread that calls run_once() on an interval."""

    def __init__(self, interval_seconds: int | None = None) -> None:
        self.interval = interval_seconds or get_settings().scheduler_interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="scheduler", daemon=True)
        self._thread.start()
        logger.info("Scheduler started", extra={"interval_seconds": self.interval})

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def join(self) -> None:
        if self._thread:
            self._thread.join()

    def _loop(self) -> None:
        while not self._stop.is_set():
            results = run_once()
            if any(v for v in results.values()):
                logger.info("Scheduler tick", extra={"results": results})
            self._stop.wait(self.interval)


