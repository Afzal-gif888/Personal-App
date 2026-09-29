"""Notifications. Scheduler jobs and the agent create them; the API lists and marks them read.

Every notification is stored in-app. Reminder-type notifications are also emailed (EmailJS) when the
user has turned on `emailNotifications`; the email outcome is recorded in `meta["email"]`.
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models import Notification, User
from app.models.enums import NotificationStatus, NotificationType
from app.services.user_service import notification_flags

# Which preference flag gates which notification type. Unlisted types are always delivered.
PREFERENCE_FOR_TYPE = {
    NotificationType.REMINDER: "reminders",
    NotificationType.TASK_DEADLINE: "reminders",
    NotificationType.BILL: "reminders",
    NotificationType.PAYMENT: "reminders",
    NotificationType.EVENT: "reminders",
    NotificationType.MEETING: "reminders",
    NotificationType.STUDY_SESSION: "studyNotifications",
    NotificationType.AGENT_ACTION: "aiNotifications",
    NotificationType.APPROVAL: "aiNotifications",
}


def wants(user: User, type_: NotificationType) -> bool:
    flag = PREFERENCE_FOR_TYPE.get(type_)
    return flag is None or bool(notification_flags(user).get(flag, True))


def notify(
    db: Session,
    user: User,
    type_: NotificationType,
    title: str,
    message: str,
    *,
    dedupe_key: str | None = None,
    scheduled_at: datetime | None = None,
    meta: dict | None = None,
) -> Notification | None:
    """Create and deliver an in-app notification. Returns None if muted by preference or a duplicate."""
    if not wants(user, type_):
        return None
    if dedupe_key and db.scalar(
        select(Notification.id).where(Notification.user_id == user.id, Notification.dedupe_key == dedupe_key)
    ):
        return None
    now = utcnow()
    notification = Notification(
        user_id=user.id,
        type=type_,
        title=title[:300],
        message=message,
        scheduled_at=scheduled_at or now,
        sent_at=now,
        status=NotificationStatus.SENT,
        channel="in_app",
        dedupe_key=dedupe_key,
        meta=meta or {},
    )
    # The unique (user_id, dedupe_key) constraint settles races between scheduler instances.
    try:
        with db.begin_nested():
            db.add(notification)
    except IntegrityError:
        return None
    # Every signed-in user proved they read this inbox (the login code went there).
    if type_ in EMAIL_TYPES and notification_flags(user).get("emailNotifications"):
        _email(user, notification)
    return notification


# Time-sensitive notifications that are also emailed when the user turns on "Email me reminders".
EMAIL_TYPES = {
    NotificationType.REMINDER,
    NotificationType.TASK_DEADLINE,
    NotificationType.BILL,
    NotificationType.PAYMENT,
    NotificationType.EVENT,
    NotificationType.MEETING,
    NotificationType.STUDY_SESSION,
}


def _email(user: User, notification: Notification) -> None:
    """Send the notification by email and record the outcome on it. Never raises."""
    from app.core.config import get_settings
    from app.notifications.emailjs import EmailError, emailjs_configured, send_template

    template = get_settings().emailjs_notification_template_id
    if not template or not emailjs_configured(template):
        outcome = {"status": "skipped", "reason": "email_not_configured"}
    else:
        # Reminders carry labelled lines (Reminder / Type / When / Notes); others show title + message.
        details = [(str(k), str(v)) for k, v in (notification.meta or {}).get("details") or []]
        summary = "\n".join(f"{k}: {v}" for k, v in details) if details else f"{notification.title}\n{notification.message}"
        body = f"{summary}\n\nOpen It's Personal: {get_settings().app_base_url.rstrip('/')}/reminders\n\n" \
               "You get this email because 'Email me reminders' is on in Settings > Notifications."
        attempts = int(((notification.meta or {}).get("email") or {}).get("attempts", 0)) + 1
        params = {"subject": f"It's Personal: {notification.title}", "message": body, "title": notification.title,
                  **{k.lower(): v for k, v in details}}  # also {{reminder}}, {{type}}, {{when}}, {{notes}}
        try:
            send_template(template, user.email, user.name, params)
            outcome = {"status": "sent", "attempts": attempts}
        except EmailError as exc:
            outcome = {"status": "failed", "error": str(exc), "attempts": attempts}
    notification.meta = {**(notification.meta or {}), "email": {**outcome, "at": utcnow().isoformat()}}


MAX_EMAIL_ATTEMPTS = 3


def retry_failed_emails(db: Session, *, limit: int = 200) -> int:
    """Re-send reminder emails that failed (e.g. mail server briefly down), up to 3 tries in 24 hours."""
    since = utcnow() - timedelta(hours=24)
    recent = db.scalars(
        select(Notification).where(Notification.created_at >= since, Notification.type.in_(EMAIL_TYPES))
        .order_by(Notification.created_at).limit(limit)
    )
    sent = 0
    for notification in recent:
        email = (notification.meta or {}).get("email") or {}
        if email.get("status") != "failed" or int(email.get("attempts", 1)) >= MAX_EMAIL_ATTEMPTS:
            continue
        user = db.get(User, notification.user_id)
        if user is None or not notification_flags(user).get("emailNotifications"):
            continue
        _email(user, notification)
        sent += notification.meta["email"]["status"] == "sent"
    return sent


def mark_read(db: Session, notification: Notification) -> None:
    if notification.read_at is None:
        notification.read_at = utcnow()
        notification.status = NotificationStatus.READ

