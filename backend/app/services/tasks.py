import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models import Task, User
from app.models.enums import Priority, TaskCategory, TaskStatus
from app.repositories.base import apply_patch, get_owned, paginate
from app.schemas.planning import TaskIn, TaskUpdate
from app.services import subjects


def list_tasks(
    db: Session,
    user: User,
    *,
    page: int,
    page_size: int,
    status: list[TaskStatus] | None = None,
    category: TaskCategory | None = None,
    priority: Priority | None = None,
    subject_id: uuid.UUID | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    q: str | None = None,
) -> tuple[list[Task], int]:
    stmt = select(Task).where(Task.user_id == user.id)
    if status:
        stmt = stmt.where(Task.status.in_(status))
    if category:
        stmt = stmt.where(Task.category == category)
    if priority:
        stmt = stmt.where(Task.priority == priority)
    if subject_id:
        stmt = stmt.where(Task.subject_id == subject_id)
    if due_from:
        stmt = stmt.where(Task.due_date >= due_from)
    if due_to:
        stmt = stmt.where(Task.due_date <= due_to)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Task.title.ilike(like), Task.description.ilike(like)))
    stmt = stmt.order_by(Task.due_date.asc().nulls_last(), Task.due_time.asc().nulls_last(), Task.created_at.desc())
    return paginate(db, stmt, page, page_size)


def get_task(db: Session, user: User, task_id: uuid.UUID) -> Task:
    return get_owned(db, Task, task_id, user.id, label="Task")


def create_task(db: Session, user: User, data: TaskIn, *, commit: bool = True) -> Task:
    values = data.model_dump(exclude={"subject", "subject_id"})
    subject = subjects.resolve(db, user, data.subject_id, data.subject)
    task = Task(user_id=user.id, subject_id=subject.id if subject else None, **values)
    task.subject = subject
    _sync_completed(task)
    db.add(task)
    db.flush()
    if commit:
        db.commit()
    return task


def update_task(db: Session, user: User, task_id: uuid.UUID, data: TaskUpdate) -> Task:
    task = get_task(db, user, task_id)
    patch = data.model_dump(exclude_unset=True)
    if "subject_id" in patch or "subject" in patch:
        subject = subjects.resolve(db, user, patch.pop("subject_id", None), patch.pop("subject", None))
        task.subject_id, task.subject = (subject.id if subject else None), subject
    apply_patch(task, patch, required=("title", "category", "priority", "status"))
    _sync_completed(task)
    db.commit()
    return task


def set_status(db: Session, user: User, task_id: uuid.UUID, status: TaskStatus, *, commit: bool = True) -> Task:
    task = get_task(db, user, task_id)
    task.status = status
    _sync_completed(task)
    if commit:
        db.commit()
    return task


def delete_task(db: Session, user: User, task_id: uuid.UUID) -> None:
    db.delete(get_task(db, user, task_id))
    db.commit()


def _sync_completed(task: Task) -> None:
    if task.status == TaskStatus.COMPLETED:
        task.completed_at = task.completed_at or utcnow()
    else:
        task.completed_at = None
