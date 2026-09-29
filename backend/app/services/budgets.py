"""Monthly budgets: a spending limit per expense category, or one overall limit, with progress."""

import uuid
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.models import Budget, Expense, User
from app.models.enums import ExpenseCategory
from app.repositories.base import apply_patch, get_owned
from app.schemas.finance import BudgetIn, BudgetUpdate
from app.services.finance import _currency, month_bounds


def list_budgets(db: Session, user: User) -> list[Budget]:
    # Overall budget first, then categories alphabetically.
    stmt = select(Budget).where(Budget.user_id == user.id).order_by(Budget.category.is_not(None), Budget.category)
    return list(db.scalars(stmt))


def get_budget(db: Session, user: User, budget_id: uuid.UUID) -> Budget:
    return get_owned(db, Budget, budget_id, user.id, label="Budget")


def find_budget(db: Session, user: User, category: ExpenseCategory | None) -> Budget | None:
    cond = Budget.category.is_(None) if category is None else Budget.category == category
    return db.scalar(select(Budget).where(Budget.user_id == user.id, cond))


def create_budget(db: Session, user: User, data: BudgetIn, *, commit: bool = True) -> Budget:
    # Checked here rather than left to the unique constraint: NULL categories never collide in SQL.
    if find_budget(db, user, data.category):
        label = data.category.value if data.category else "overall spending"
        raise ConflictError(f"A budget for {label} already exists; update it instead")
    budget = Budget(user_id=user.id, **data.model_dump(), currency=_currency(user, None))
    db.add(budget)
    db.flush()
    if commit:
        db.commit()
    return budget


def update_budget(db: Session, user: User, budget_id: uuid.UUID, data: BudgetUpdate, *, commit: bool = True) -> Budget:
    budget = get_budget(db, user, budget_id)
    apply_patch(budget, data.model_dump(exclude_unset=True), required=("amount", "alert_threshold"))
    db.flush()
    if commit:
        db.commit()
    return budget


def delete_budget(db: Session, user: User, budget_id: uuid.UUID) -> None:
    db.delete(get_budget(db, user, budget_id))
    db.commit()


def _spending(db: Session, user: User, currency: str, start: date, end: date) -> dict[ExpenseCategory, Decimal]:
    rows = db.execute(
        select(Expense.category, func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.user_id == user.id,
            Expense.currency == currency,
            Expense.expense_date >= start,
            Expense.expense_date <= end,
        )
        .group_by(Expense.category)
    ).all()
    return {c: Decimal(t) for c, t in rows}


def progress(budget: Budget, spent: Decimal, month: str) -> dict:
    percent = int(spent * 100 / budget.amount) if budget.amount else 0
    if spent > budget.amount:
        status = "over"
    elif percent >= budget.alert_threshold:
        status = "warning"
    else:
        status = "on_track"
    return {
        **{c.key: getattr(budget, c.key) for c in budget.__table__.columns},
        "month": month,
        "spent": spent,
        "remaining": max(budget.amount - spent, Decimal("0")),
        "percent_used": percent,
        "status": status,
    }


def budgets_with_progress(db: Session, user: User, tz: ZoneInfo, month: str | None = None) -> list[dict]:
    start, end, label = month_bounds(month, tz)
    items = list_budgets(db, user)
    cache: dict[str, dict[ExpenseCategory, Decimal]] = {}
    out = []
    for b in items:
        if b.currency not in cache:
            cache[b.currency] = _spending(db, user, b.currency, start, end)
        by_cat = cache[b.currency]
        spent = sum(by_cat.values(), Decimal("0")) if b.category is None else by_cat.get(b.category, Decimal("0"))
        out.append(progress(b, spent, label))
    return out


def budget_with_progress(db: Session, user: User, tz: ZoneInfo, budget: Budget) -> dict:
    return next(p for p in budgets_with_progress(db, user, tz) if p["id"] == budget.id)
