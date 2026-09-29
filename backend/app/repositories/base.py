"""Query helpers shared by services. Every lookup is scoped to the owning user."""

import uuid
from typing import TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationFailed

M = TypeVar("M")


def get_owned(db: Session, model: type[M], obj_id: uuid.UUID, user_id: uuid.UUID, *, label: str | None = None) -> M:
    obj = db.scalar(select(model).filter_by(id=obj_id, user_id=user_id))
    if obj is None:
        # Same response whether the row is missing or owned by someone else.
        raise NotFoundError(f"{label or model.__name__} not found")
    return obj


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> tuple[list, int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).unique())
    return items, total


def apply_patch(obj, data: dict, *, required: tuple[str, ...] = ()) -> None:
    """Apply a PATCH payload (already exclude_unset). Explicit nulls on required fields are rejected."""
    for field in required:
        if field in data and data[field] is None:
            raise ValidationFailed(f"{field} cannot be null")
    for key, value in data.items():
        setattr(obj, key, value)
