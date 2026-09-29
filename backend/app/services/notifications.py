"""In-app notification inbox. Creation lives in app.notifications (used by the scheduler and approvals)."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models import Notification, User
from app.models.enums import NotificationStatus
from app.notifications import mark_read
from app.repositories.base import get_owned, paginate


def list_notifications(
    db: Session, user: User, *, page: int, page_size: int, unread_only: bool = False
) -> tuple[list[Notification], int]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return paginate(db, stmt.order_by(Notification.created_at.desc()), page, page_size)


def unread_count(db: Session, user: User) -> int:
    return db.scalar(select(func.count()).where(Notification.user_id == user.id, Notification.read_at.is_(None))) or 0


def read_all(db: Session, user: User) -> None:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=utcnow(), status=NotificationStatus.READ)
    )
    db.commit()


def read_one(db: Session, user: User, notification_id: uuid.UUID) -> Notification:
    notification = get_owned(db, Notification, notification_id, user.id, label="Notification")
    mark_read(db, notification)
    db.commit()
    return notification


def delete(db: Session, user: User, notification_id: uuid.UUID) -> None:
    db.delete(get_owned(db, Notification, notification_id, user.id, label="Notification"))
    db.commit()
