import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.models import Subject, User
from app.repositories.base import apply_patch, get_owned
from app.schemas.planning import SubjectIn, SubjectUpdate


def list_subjects(db: Session, user: User) -> list[Subject]:
    return list(db.scalars(select(Subject).where(Subject.user_id == user.id).order_by(Subject.name)))


def get_subject(db: Session, user: User, subject_id: uuid.UUID) -> Subject:
    return get_owned(db, Subject, subject_id, user.id, label="Subject")


def resolve(db: Session, user: User, subject_id: uuid.UUID | None, name: str | None) -> Subject | None:
    """Validate an explicit subject id, or match/create one by name."""
    if subject_id:
        return get_subject(db, user, subject_id)
    if not name or not name.strip():
        return None
    name = name.strip()
    existing = db.scalar(
        select(Subject).where(Subject.user_id == user.id, func.lower(Subject.name) == name.lower())
    )
    if existing:
        return existing
    subject = Subject(user_id=user.id, name=name[:200])
    db.add(subject)
    db.flush()
    return subject


def create_subject(db: Session, user: User, data: SubjectIn) -> Subject:
    subject = Subject(user_id=user.id, **data.model_dump())
    db.add(subject)
    _commit_unique(db)
    return subject


def update_subject(db: Session, user: User, subject_id: uuid.UUID, data: SubjectUpdate) -> Subject:
    subject = get_subject(db, user, subject_id)
    apply_patch(subject, data.model_dump(exclude_unset=True), required=("name",))
    _commit_unique(db)
    return subject


def delete_subject(db: Session, user: User, subject_id: uuid.UUID) -> None:
    db.delete(get_subject(db, user, subject_id))
    db.commit()


def _commit_unique(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A subject with this code already exists")
