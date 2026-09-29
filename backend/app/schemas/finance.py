import uuid
from datetime import date as Date
from typing import Literal

from pydantic import Field, model_validator

from app.models.enums import (
    BillCategory,
    BillStatus,
    ExpenseCategory,
    Frequency,
    PaymentPlanStatus,
    PaymentStatus,
    SubscriptionStatus,
)
from app.schemas.common import APIModel, Currency, InputModel, Money, MoneyIn, UTCDateTime

Title = Field(min_length=1, max_length=300)
Notes = Field(default=None, max_length=10_000)
Method = Field(default=None, max_length=100)


# --- Bills ----------------------------------------------------------------------------------------


class BillIn(InputModel):
    title: str = Title
    category: BillCategory = BillCategory.OTHER
    amount: MoneyIn
    currency: Currency | None = None  # defaults to the user's preferred currency
    due_date: Date
    recurring: bool = False
    frequency: Frequency | None = None
    payment_method: str | None = Method
    notes: str | None = Notes

    @model_validator(mode="after")
    def _frequency(self):
        if self.recurring and self.frequency in (None, Frequency.ONE_TIME):
            raise ValueError("Recurring bills need a frequency")
        return self


class BillUpdate(InputModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    category: BillCategory | None = None
    amount: MoneyIn | None = None
    currency: Currency | None = None
    due_date: Date | None = None
    status: BillStatus | None = None
    recurring: bool | None = None
    frequency: Frequency | None = None
    payment_method: str | None = Method
    notes: str | None = Notes


class BillPayIn(InputModel):
    amount: MoneyIn | None = None  # defaults to the bill amount
    payment_date: Date | None = None  # defaults to today in the user's timezone
    payment_method: str | None = Method
    notes: str | None = Notes


class BillOut(APIModel):
    id: uuid.UUID
    title: str
    category: BillCategory
    amount: Money
    currency: str
    due_date: Date
    status: BillStatus
    recurring: bool
    frequency: Frequency | None
    payment_method: str | None
    notes: str | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


# --- Payments -------------------------------------------------------------------------------------


class PaymentIn(InputModel):
    amount: MoneyIn
    currency: Currency | None = None
    payment_date: Date
    payment_method: str | None = Method
    status: PaymentStatus = PaymentStatus.COMPLETED
    notes: str | None = Notes
    bill_id: uuid.UUID | None = None
    payment_plan_id: uuid.UUID | None = None


class PaymentOut(APIModel):
    id: uuid.UUID
    bill_id: uuid.UUID | None
    payment_plan_id: uuid.UUID | None
    amount: Money
    currency: str
    payment_date: Date
    payment_method: str | None
    status: PaymentStatus
    notes: str | None
    created_at: UTCDateTime


class BillPaymentOut(APIModel):
    bill: BillOut
    payment: PaymentOut
    next_bill: BillOut | None = None


# --- Payment plans --------------------------------------------------------------------------------


class PaymentPlanIn(InputModel):
    title: str = Title
    description: str | None = Notes
    total_amount: MoneyIn
    installment_amount: MoneyIn
    currency: Currency | None = None
    frequency: Frequency = Frequency.MONTHLY
    start_date: Date
    end_date: Date | None = None
    next_payment_date: Date | None = None  # defaults to start_date
    total_installments: int | None = Field(default=None, ge=1, le=1000)  # derived from the amounts if omitted
    completed_installments: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _amounts(self):
        if self.installment_amount <= 0:
            raise ValueError("installmentAmount must be greater than zero")
        if self.installment_amount > self.total_amount:
            raise ValueError("installmentAmount cannot exceed totalAmount")
        return self


class PaymentPlanUpdate(InputModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Notes
    frequency: Frequency | None = None
    end_date: Date | None = None
    next_payment_date: Date | None = None
    status: PaymentPlanStatus | None = None


class InstallmentIn(InputModel):
    amount: MoneyIn | None = None  # defaults to the installment amount
    payment_date: Date | None = None
    payment_method: str | None = Method
    notes: str | None = Notes


class PaymentPlanOut(APIModel):
    id: uuid.UUID
    title: str
    description: str | None
    total_amount: Money
    installment_amount: Money
    currency: str
    frequency: Frequency
    start_date: Date
    end_date: Date | None
    next_payment_date: Date | None
    remaining_amount: Money
    total_installments: int
    completed_installments: int
    status: PaymentPlanStatus
    created_at: UTCDateTime
    updated_at: UTCDateTime


# --- Expenses -------------------------------------------------------------------------------------


class ExpenseIn(InputModel):
    title: str = Title
    description: str | None = Notes
    category: ExpenseCategory = ExpenseCategory.OTHER
    amount: MoneyIn
    currency: Currency | None = None
    expense_date: Date
    payment_method: str | None = Method


class ExpenseUpdate(InputModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Notes
    category: ExpenseCategory | None = None
    amount: MoneyIn | None = None
    currency: Currency | None = None
    expense_date: Date | None = None
    payment_method: str | None = Method


class ExpenseOut(APIModel):
    id: uuid.UUID
    title: str
    description: str | None
    category: ExpenseCategory
    amount: Money
    currency: str
    expense_date: Date
    payment_method: str | None
    created_at: UTCDateTime


class CategoryTotal(APIModel):
    category: ExpenseCategory
    total: Money
    count: int


class ExpenseSummary(APIModel):
    month: str  # YYYY-MM
    currency: str
    total: Money
    count: int
    by_category: list[CategoryTotal]


# --- Subscriptions --------------------------------------------------------------------------------


class SubscriptionIn(InputModel):
    name: str = Field(min_length=1, max_length=200)
    amount: MoneyIn
    currency: Currency | None = None
    billing_cycle: Frequency = Frequency.MONTHLY
    next_billing_date: Date | None = None
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    notes: str | None = Notes


class SubscriptionUpdate(InputModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    amount: MoneyIn | None = None
    currency: Currency | None = None
    billing_cycle: Frequency | None = None
    next_billing_date: Date | None = None
    status: SubscriptionStatus | None = None
    notes: str | None = Notes


class SubscriptionOut(APIModel):
    id: uuid.UUID
    name: str
    amount: Money
    currency: str
    billing_cycle: Frequency
    next_billing_date: Date | None
    status: SubscriptionStatus
    notes: str | None
    created_at: UTCDateTime


# --- Budgets --------------------------------------------------------------------------------------


class BudgetIn(InputModel):
    category: ExpenseCategory | None = None  # omitted/null = one overall budget for all spending
    amount: MoneyIn
    alert_threshold: int = Field(default=80, ge=1, le=100)

    @model_validator(mode="after")
    def _positive(self):
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
        return self


class BudgetUpdate(InputModel):
    amount: MoneyIn | None = None
    alert_threshold: int | None = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def _positive(self):
        if self.amount is not None and self.amount <= 0:
            raise ValueError("amount must be greater than zero")
        return self


class BudgetOut(APIModel):
    id: uuid.UUID
    category: ExpenseCategory | None
    amount: Money
    currency: str
    alert_threshold: int
    # Progress for `month` (the requested month, default this month).
    month: str
    spent: Money
    remaining: Money
    percent_used: int
    status: Literal["on_track", "warning", "over"]
    created_at: UTCDateTime
    updated_at: UTCDateTime
