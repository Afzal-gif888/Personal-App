import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Goal, User
from app.models.enums import GoalCategory, GoalStatus
from app.repositories.base import apply_patch, get_owned
from app.schemas.planning import GoalIn, GoalUpdate


def list_goals(
    db: Session, user: User, *, status: GoalStatus | None = None, category: GoalCategory | None = None
) -> list[Goal]:
    stmt = select(Goal).where(Goal.user_id == user.id)
    if status:
        stmt = stmt.where(Goal.status == status)
    if category:
        stmt = stmt.where(Goal.category == category)
    return list(db.scalars(stmt.order_by(Goal.deadline.asc().nulls_last(), Goal.created_at)))


def get_goal(db: Session, user: User, goal_id: uuid.UUID) -> Goal:
    return get_owned(db, Goal, goal_id, user.id, label="Goal")


def create_goal(db: Session, user: User, data: GoalIn) -> Goal:
    goal = Goal(user_id=user.id, **data.model_dump())
    db.add(goal)
    db.commit()
    return goal


def update_goal(db: Session, user: User, goal_id: uuid.UUID, data: GoalUpdate) -> Goal:
    goal = get_goal(db, user, goal_id)
    apply_patch(goal, data.model_dump(exclude_unset=True), required=("title", "category", "status"))
    db.commit()
    return goal


def delete_goal(db: Session, user: User, goal_id: uuid.UUID) -> None:
    db.delete(get_goal(db, user, goal_id))
    db.commit()
