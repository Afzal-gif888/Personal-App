"""Bills, payments, payment plans, expenses and subscriptions. Tracking only: no money moves."""

import math
import uuid
from datetime import date, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ValidationFailed
from app.core.timeutils import local_today
from app.models import Bill, Expense, Payment, PaymentPlan, Subscription, User
from app.models.enums import (
    BillStatus,
    ExpenseCategory,
    Frequency,
    PaymentPlanStatus,
    PaymentStatus,
    SubscriptionStatus,
)
from app.repositories.base import apply_patch, get_owned, paginate
from app.schemas.finance import (
    BillIn,
    BillPayIn,
    BillUpdate,
    ExpenseIn,
    ExpenseUpdate,
    InstallmentIn,
    PaymentIn,
    PaymentPlanIn,
    PaymentPlanUpdate,
    SubscriptionIn,
    SubscriptionUpdate,
)
from app.services.recurrence import advance

DUE_SOON_DAYS = 3
OPEN_BILL_STATUSES = (BillStatus.UPCOMING, BillStatus.DUE, BillStatus.OVERDUE)


def _currency(user: User, value: str | None) -> str:
    return value or (user.preferences.currency if user.preferences else "INR")


# --- Bills ----------------------------------------------------------------------------------------


def bill_status_for(due: date, today: date) -> BillStatus:
    if due < today:
        return BillStatus.OVERDUE
    if due <= today + timedelta(days=DUE_SOON_DAYS):
        return BillStatus.DUE
    return BillStatus.UPCOMING


def refresh_bill_statuses(db: Session, user: User, tz: ZoneInfo) -> list[Bill]:
    """Move open bills between upcoming/due/overdue as dates pass. Returns the bills that changed."""
    today = local_today(tz)
    changed = []
    for bill in db.scalars(select(Bill).where(Bill.user_id == user.id, Bill.status.in_(OPEN_BILL_STATUSES))):
        status = bill_status_for(bill.due_date, today)
        if bill.status != status:
            bill.status = status
            changed.append(bill)
    return changed


def list_bills(
    db: Session,
    user: User,
    tz: ZoneInfo,
    *,
    status: list[BillStatus] | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
) -> list[Bill]:
    if refresh_bill_statuses(db, user, tz):
        db.commit()
    stmt = select(Bill).where(Bill.user_id == user.id)
    if status:
        stmt = stmt.where(Bill.status.in_(status))
    if due_from:
        stmt = stmt.where(Bill.due_date >= due_from)
    if due_to:
        stmt = stmt.where(Bill.due_date <= due_to)
    return list(db.scalars(stmt.order_by(Bill.due_date, Bill.title)))


def get_bill(db: Session, user: User, bill_id: uuid.UUID) -> Bill:
    return get_owned(db, Bill, bill_id, user.id, label="Bill")


def create_bill(db: Session, user: User, tz: ZoneInfo, data: BillIn) -> Bill:
    bill = Bill(
        user_id=user.id,
        **data.model_dump(exclude={"currency"}),
        currency=_currency(user, data.currency),
        status=bill_status_for(data.due_date, local_today(tz)),
    )
    db.add(bill)
    db.commit()
    return bill


def update_bill(db: Session, user: User, tz: ZoneInfo, bill_id: uuid.UUID, data: BillUpdate) -> Bill:
    bill = get_bill(db, user, bill_id)
    patch = data.model_dump(exclude_unset=True)
    apply_patch(bill, patch, required=("title", "category", "amount", "currency", "due_date", "status", "recurring"))
    if bill.recurring and bill.frequency in (None, Frequency.ONE_TIME):
        raise ValidationFailed("Recurring bills need a frequency")
    if "due_date" in patch and "status" not in patch and bill.status in OPEN_BILL_STATUSES:
        bill.status = bill_status_for(bill.due_date, local_today(tz))
    db.commit()
    return bill


def pay_bill(
    db: Session, user: User, tz: ZoneInfo, bill_id: uuid.UUID, data: BillPayIn, *, commit: bool = True
) -> tuple[Bill, Payment, Bill | None]:
    """Record a payment, mark the bill paid and, for recurring bills, create the next occurrence."""
    bill = get_bill(db, user, bill_id)
    if bill.status in (BillStatus.PAID, BillStatus.CANCELLED):
        raise ConflictError(f"Bill is already {bill.status.value}")
    payment = Payment(
        user_id=user.id,
        bill_id=bill.id,
        amount=data.amount if data.amount is not None else bill.amount,
        currency=bill.currency,
        payment_date=data.payment_date or local_today(tz),
        payment_method=data.payment_method or bill.payment_method,
        status=PaymentStatus.COMPLETED,
        notes=data.notes,
    )
    bill.status = BillStatus.PAID
    db.add(payment)

    next_bill = None
    if bill.recurring and bill.frequency and (next_due := advance(bill.due_date, bill.frequency)):
        next_bill = Bill(
            user_id=user.id,
            title=bill.title,
            category=bill.category,
            amount=bill.amount,
            currency=bill.currency,
            due_date=next_due,
            status=bill_status_for(next_due, local_today(tz)),
            recurring=True,
            frequency=bill.frequency,
            payment_method=bill.payment_method,
            notes=bill.notes,
        )
        db.add(next_bill)
    db.flush()
    if commit:
        db.commit()
    return bill, payment, next_bill


def delete_bill(db: Session, user: User, bill_id: uuid.UUID) -> None:
    db.delete(get_bill(db, user, bill_id))
    db.commit()


# --- Payments -------------------------------------------------------------------------------------


def list_payments(
    db: Session,
    user: User,
    *,
    page: int,
    page_size: int,
    bill_id: uuid.UUID | None = None,
    payment_plan_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[Payment], int]:
    stmt = select(Payment).where(Payment.user_id == user.id)
    if bill_id:
        stmt = stmt.where(Payment.bill_id == bill_id)
    if payment_plan_id:
        stmt = stmt.where(Payment.payment_plan_id == payment_plan_id)
    if date_from:
        stmt = stmt.where(Payment.payment_date >= date_from)
    if date_to:
        stmt = stmt.where(Payment.payment_date <= date_to)
    return paginate(db, stmt.order_by(Payment.payment_date.desc(), Payment.created_at.desc()), page, page_size)


def create_payment(db: Session, user: User, data: PaymentIn) -> Payment:
    """A standalone record. Use the bill/plan endpoints to also update the bill or plan."""
    if data.bill_id:
        get_bill(db, user, data.bill_id)
    if data.payment_plan_id:
        get_plan(db, user, data.payment_plan_id)
    payment = Payment(user_id=user.id, **data.model_dump(exclude={"currency"}), currency=_currency(user, data.currency))
    db.add(payment)
    db.commit()
    return payment


def delete_payment(db: Session, user: User, payment_id: uuid.UUID) -> None:
    db.delete(get_owned(db, Payment, payment_id, user.id, label="Payment"))
    db.commit()


# --- Payment plans --------------------------------------------------------------------------------


def list_plans(db: Session, user: User, *, status: PaymentPlanStatus | None = None) -> list[PaymentPlan]:
    stmt = select(PaymentPlan).where(PaymentPlan.user_id == user.id)
    if status:
        stmt = stmt.where(PaymentPlan.status == status)
    return list(db.scalars(stmt.order_by(PaymentPlan.next_payment_date.asc().nulls_last(), PaymentPlan.title)))


def get_plan(db: Session, user: User, plan_id: uuid.UUID) -> PaymentPlan:
    return get_owned(db, PaymentPlan, plan_id, user.id, label="Payment plan")


def create_plan(db: Session, user: User, data: PaymentPlanIn) -> PaymentPlan:
    total_installments = data.total_installments or math.ceil(data.total_amount / data.installment_amount)
    if data.completed_installments > total_installments:
        raise ValidationFailed("completedInstallments cannot exceed totalInstallments")
    paid = min(data.total_amount, data.installment_amount * data.completed_installments)
    done = data.completed_installments >= total_installments
    plan = PaymentPlan(
        user_id=user.id,
        **data.model_dump(exclude={"currency", "total_installments", "next_payment_date"}),
        currency=_currency(user, data.currency),
        total_installments=total_installments,
        remaining_amount=data.total_amount - paid,
        next_payment_date=None if done else (data.next_payment_date or data.start_date),
        status=PaymentPlanStatus.COMPLETED if done else PaymentPlanStatus.ACTIVE,
    )
    db.add(plan)
    db.commit()
    return plan


def update_plan(db: Session, user: User, plan_id: uuid.UUID, data: PaymentPlanUpdate) -> PaymentPlan:
    plan = get_plan(db, user, plan_id)
    apply_patch(plan, data.model_dump(exclude_unset=True), required=("title", "frequency", "status"))
    db.commit()
    return plan


def record_installment(
    db: Session, user: User, tz: ZoneInfo, plan_id: uuid.UUID, data: InstallmentIn
) -> tuple[PaymentPlan, Payment]:
    plan = get_plan(db, user, plan_id)
    if plan.status != PaymentPlanStatus.ACTIVE:
        raise ConflictError(f"Payment plan is {plan.status.value}")
    amount = data.amount if data.amount is not None else min(plan.installment_amount, plan.remaining_amount)
    payment = Payment(
        user_id=user.id,
        payment_plan_id=plan.id,
        amount=amount,
        currency=plan.currency,
        payment_date=data.payment_date or local_today(tz),
        payment_method=data.payment_method,
        status=PaymentStatus.COMPLETED,
        notes=data.notes,
    )
    plan.completed_installments += 1
    plan.remaining_amount = max(Decimal("0"), plan.remaining_amount - amount)
    if plan.completed_installments >= plan.total_installments or plan.remaining_amount == 0:
        plan.status = PaymentPlanStatus.COMPLETED
        plan.next_payment_date = None
    elif plan.next_payment_date:
        plan.next_payment_date = advance(plan.next_payment_date, plan.frequency) or plan.next_payment_date
    db.add(payment)
    db.commit()
    return plan, payment


def delete_plan(db: Session, user: User, plan_id: uuid.UUID) -> None:
    db.delete(get_plan(db, user, plan_id))
    db.commit()


# --- Expenses -------------------------------------------------------------------------------------


def list_expenses(
    db: Session,
    user: User,
    *,
    page: int,
    page_size: int,
    category: ExpenseCategory | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
) -> tuple[list[Expense], int]:
    stmt = select(Expense).where(Expense.user_id == user.id)
    if category:
        stmt = stmt.where(Expense.category == category)
    if date_from:
        stmt = stmt.where(Expense.expense_date >= date_from)
    if date_to:
        stmt = stmt.where(Expense.expense_date <= date_to)
    if q:
        stmt = stmt.where(Expense.title.ilike(f"%{q.strip()}%"))
    return paginate(db, stmt.order_by(Expense.expense_date.desc(), Expense.created_at.desc()), page, page_size)


def get_expense(db: Session, user: User, expense_id: uuid.UUID) -> Expense:
    return get_owned(db, Expense, expense_id, user.id, label="Expense")


def create_expense(db: Session, user: User, data: ExpenseIn, *, commit: bool = True) -> Expense:
    expense = Expense(user_id=user.id, **data.model_dump(exclude={"currency"}), currency=_currency(user, data.currency))
    db.add(expense)
    db.flush()
    if commit:
        db.commit()
    return expense


def update_expense(db: Session, user: User, expense_id: uuid.UUID, data: ExpenseUpdate) -> Expense:
    expense = get_expense(db, user, expense_id)
    apply_patch(
        expense, data.model_dump(exclude_unset=True), required=("title", "category", "amount", "currency", "expense_date")
    )
    db.commit()
    return expense


def delete_expense(db: Session, user: User, expense_id: uuid.UUID) -> None:
    db.delete(get_expense(db, user, expense_id))
    db.commit()


def month_bounds(month: str | None, tz: ZoneInfo) -> tuple[date, date, str]:
    if month:
        try:
            year, mon = (int(p) for p in month.split("-"))
            start = date(year, mon, 1)
        except ValueError:
            raise ValidationFailed("month must be YYYY-MM")
    else:
        start = local_today(tz).replace(day=1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return start, end, f"{start:%Y-%m}"


def expense_summary(db: Session, user: User, tz: ZoneInfo, month: str | None) -> dict:
    """Totals for one month. Amounts in other currencies are reported separately, never summed together."""
    start, end, label = month_bounds(month, tz)
    currency = _currency(user, None)
    rows = db.execute(
        select(Expense.category, func.coalesce(func.sum(Expense.amount), 0), func.count())
        .where(
            Expense.user_id == user.id,
            Expense.currency == currency,
            Expense.expense_date >= start,
            Expense.expense_date <= end,
        )
        .group_by(Expense.category)
    ).all()
    by_category = sorted(
        ({"category": c, "total": Decimal(t), "count": n} for c, t, n in rows), key=lambda r: r["total"], reverse=True
    )
    return {
        "month": label,
        "currency": currency,
        "total": sum((r["total"] for r in by_category), Decimal("0")),
        "count": sum(r["count"] for r in by_category),
        "by_category": by_category,
    }


# --- Subscriptions --------------------------------------------------------------------------------


def list_subscriptions(db: Session, user: User, *, status: SubscriptionStatus | None = None) -> list[Subscription]:
    stmt = select(Subscription).where(Subscription.user_id == user.id)
    if status:
        stmt = stmt.where(Subscription.status == status)
    return list(db.scalars(stmt.order_by(Subscription.next_billing_date.asc().nulls_last(), Subscription.name)))


def get_subscription(db: Session, user: User, sub_id: uuid.UUID) -> Subscription:
    return get_owned(db, Subscription, sub_id, user.id, label="Subscription")


def create_subscription(db: Session, user: User, data: SubscriptionIn) -> Subscription:
    sub = Subscription(user_id=user.id, **data.model_dump(exclude={"currency"}), currency=_currency(user, data.currency))
    db.add(sub)
    db.commit()
    return sub


def update_subscription(db: Session, user: User, sub_id: uuid.UUID, data: SubscriptionUpdate) -> Subscription:
    sub = get_subscription(db, user, sub_id)
    apply_patch(sub, data.model_dump(exclude_unset=True), required=("name", "amount", "currency", "billing_cycle", "status"))
    db.commit()
    return sub


def delete_subscription(db: Session, user: User, sub_id: uuid.UUID) -> None:
    db.delete(get_subscription(db, user, sub_id))
    db.commit()
