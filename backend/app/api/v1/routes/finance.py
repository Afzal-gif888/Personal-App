"""Bills, payments, payment plans, expenses, subscriptions and budgets."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DB, CurrentUser, Paging, UserZone
from app.models.enums import BillStatus, ExpenseCategory, PaymentPlanStatus, SubscriptionStatus
from app.schemas.common import Page
from app.schemas.finance import (
    BillIn,
    BillOut,
    BillPayIn,
    BillPaymentOut,
    BillUpdate,
    BudgetIn,
    BudgetOut,
    BudgetUpdate,
    ExpenseIn,
    ExpenseOut,
    ExpenseSummary,
    ExpenseUpdate,
    InstallmentIn,
    PaymentIn,
    PaymentOut,
    PaymentPlanIn,
    PaymentPlanOut,
    PaymentPlanUpdate,
    SubscriptionIn,
    SubscriptionOut,
    SubscriptionUpdate,
)
from app.services import budgets, finance

router = APIRouter()

# --- Bills ----------------------------------------------------------------------------------------


@router.get("/bills", response_model=list[BillOut], tags=["bills"])
def list_bills(
    user: CurrentUser,
    db: DB,
    tz: UserZone,
    bill_status: Annotated[list[BillStatus] | None, Query(alias="status")] = None,
    due_from: date | None = None,
    due_to: date | None = None,
):
    return finance.list_bills(db, user, tz, status=bill_status, due_from=due_from, due_to=due_to)


@router.post("/bills", response_model=BillOut, status_code=201, tags=["bills"])
def create_bill(data: BillIn, user: CurrentUser, db: DB, tz: UserZone):
    return finance.create_bill(db, user, tz, data)


@router.get("/bills/{bill_id}", response_model=BillOut, tags=["bills"])
def get_bill(bill_id: uuid.UUID, user: CurrentUser, db: DB):
    return finance.get_bill(db, user, bill_id)


@router.patch("/bills/{bill_id}", response_model=BillOut, tags=["bills"])
def update_bill(bill_id: uuid.UUID, data: BillUpdate, user: CurrentUser, db: DB, tz: UserZone):
    return finance.update_bill(db, user, tz, bill_id, data)


@router.post("/bills/{bill_id}/pay", response_model=BillPaymentOut, tags=["bills"])
def pay_bill(bill_id: uuid.UUID, user: CurrentUser, db: DB, tz: UserZone, data: BillPayIn | None = None):
    """Record that the bill was paid (no money moves). Recurring bills get their next occurrence created."""
    bill, payment, next_bill = finance.pay_bill(db, user, tz, bill_id, data or BillPayIn())
    return BillPaymentOut(
        bill=BillOut.model_validate(bill),
        payment=PaymentOut.model_validate(payment),
        next_bill=BillOut.model_validate(next_bill) if next_bill else None,
    )


@router.delete("/bills/{bill_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["bills"])
def delete_bill(bill_id: uuid.UUID, user: CurrentUser, db: DB):
    finance.delete_bill(db, user, bill_id)


# --- Payments -------------------------------------------------------------------------------------


@router.get("/payments", response_model=Page[PaymentOut], tags=["payments"])
def list_payments(
    user: CurrentUser,
    db: DB,
    paging: Paging,
    bill_id: uuid.UUID | None = None,
    payment_plan_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    items, total = finance.list_payments(
        db, user, page=paging.page, page_size=paging.page_size, bill_id=bill_id,
        payment_plan_id=payment_plan_id, date_from=date_from, date_to=date_to,
    )
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@router.post("/payments", response_model=PaymentOut, status_code=201, tags=["payments"])
def create_payment(data: PaymentIn, user: CurrentUser, db: DB):
    return finance.create_payment(db, user, data)


@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["payments"])
def delete_payment(payment_id: uuid.UUID, user: CurrentUser, db: DB):
    finance.delete_payment(db, user, payment_id)


# --- Payment plans --------------------------------------------------------------------------------


@router.get("/payment-plans", response_model=list[PaymentPlanOut], tags=["payment-plans"])
def list_payment_plans(
    user: CurrentUser, db: DB, plan_status: Annotated[PaymentPlanStatus | None, Query(alias="status")] = None
):
    return finance.list_plans(db, user, status=plan_status)


@router.post("/payment-plans", response_model=PaymentPlanOut, status_code=201, tags=["payment-plans"])
def create_payment_plan(data: PaymentPlanIn, user: CurrentUser, db: DB):
    return finance.create_plan(db, user, data)


@router.get("/payment-plans/{plan_id}", response_model=PaymentPlanOut, tags=["payment-plans"])
def get_payment_plan(plan_id: uuid.UUID, user: CurrentUser, db: DB):
    return finance.get_plan(db, user, plan_id)


@router.patch("/payment-plans/{plan_id}", response_model=PaymentPlanOut, tags=["payment-plans"])
def update_payment_plan(plan_id: uuid.UUID, data: PaymentPlanUpdate, user: CurrentUser, db: DB):
    return finance.update_plan(db, user, plan_id, data)


@router.post("/payment-plans/{plan_id}/payments", response_model=PaymentPlanOut, tags=["payment-plans"])
def record_installment(
    plan_id: uuid.UUID, user: CurrentUser, db: DB, tz: UserZone, data: InstallmentIn | None = None
):
    plan, _ = finance.record_installment(db, user, tz, plan_id, data or InstallmentIn())
    return plan


@router.delete("/payment-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["payment-plans"])
def delete_payment_plan(plan_id: uuid.UUID, user: CurrentUser, db: DB):
    finance.delete_plan(db, user, plan_id)


# --- Expenses -------------------------------------------------------------------------------------


@router.get("/expenses", response_model=Page[ExpenseOut], tags=["expenses"])
def list_expenses(
    user: CurrentUser,
    db: DB,
    paging: Paging,
    category: ExpenseCategory | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
):
    items, total = finance.list_expenses(
        db, user, page=paging.page, page_size=paging.page_size, category=category,
        date_from=date_from, date_to=date_to, q=q,
    )
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@router.get("/expenses/summary", response_model=ExpenseSummary, tags=["expenses"])
def expense_summary(
    user: CurrentUser, db: DB, tz: UserZone, month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None
):
    """Monthly totals by category, in the user's currency."""
    return finance.expense_summary(db, user, tz, month)


@router.post("/expenses", response_model=ExpenseOut, status_code=201, tags=["expenses"])
def create_expense(data: ExpenseIn, user: CurrentUser, db: DB):
    return finance.create_expense(db, user, data)


@router.patch("/expenses/{expense_id}", response_model=ExpenseOut, tags=["expenses"])
def update_expense(expense_id: uuid.UUID, data: ExpenseUpdate, user: CurrentUser, db: DB):
    return finance.update_expense(db, user, expense_id, data)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["expenses"])
def delete_expense(expense_id: uuid.UUID, user: CurrentUser, db: DB):
    finance.delete_expense(db, user, expense_id)


# --- Subscriptions --------------------------------------------------------------------------------


@router.get("/subscriptions", response_model=list[SubscriptionOut], tags=["subscriptions"])
def list_subscriptions(
    user: CurrentUser, db: DB, sub_status: Annotated[SubscriptionStatus | None, Query(alias="status")] = None
):
    return finance.list_subscriptions(db, user, status=sub_status)


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=201, tags=["subscriptions"])
def create_subscription(data: SubscriptionIn, user: CurrentUser, db: DB):
    return finance.create_subscription(db, user, data)


@router.patch("/subscriptions/{sub_id}", response_model=SubscriptionOut, tags=["subscriptions"])
def update_subscription(sub_id: uuid.UUID, data: SubscriptionUpdate, user: CurrentUser, db: DB):
    return finance.update_subscription(db, user, sub_id, data)


@router.delete("/subscriptions/{sub_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["subscriptions"])
def delete_subscription(sub_id: uuid.UUID, user: CurrentUser, db: DB):
    finance.delete_subscription(db, user, sub_id)


# --- Budgets --------------------------------------------------------------------------------------


@router.get("/budgets", response_model=list[BudgetOut], tags=["budgets"])
def list_budgets(
    user: CurrentUser, db: DB, tz: UserZone, month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None
):
    """Every budget with its spending progress for `month` (YYYY-MM, default this month)."""
    return budgets.budgets_with_progress(db, user, tz, month)


@router.post("/budgets", response_model=BudgetOut, status_code=201, tags=["budgets"])
def create_budget(data: BudgetIn, user: CurrentUser, db: DB, tz: UserZone):
    return budgets.budget_with_progress(db, user, tz, budgets.create_budget(db, user, data))


@router.patch("/budgets/{budget_id}", response_model=BudgetOut, tags=["budgets"])
def update_budget(budget_id: uuid.UUID, data: BudgetUpdate, user: CurrentUser, db: DB, tz: UserZone):
    return budgets.budget_with_progress(db, user, tz, budgets.update_budget(db, user, budget_id, data))


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["budgets"])
def delete_budget(budget_id: uuid.UUID, user: CurrentUser, db: DB):
    budgets.delete_budget(db, user, budget_id)
