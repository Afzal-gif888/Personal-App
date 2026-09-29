"""Financial tracking only — no payment processing or bank integrations."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UserOwned, UUIDPk, str_enum
from app.models.enums import (
    BillCategory,
    BillStatus,
    ExpenseCategory,
    Frequency,
    PaymentPlanStatus,
    PaymentStatus,
    SubscriptionStatus,
)

Money = Numeric(12, 2)


class Bill(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "bills"
    __table_args__ = (
        Index("ix_bills_user_status_due", "user_id", "status", "due_date"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
    )

    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[BillCategory] = mapped_column(str_enum(BillCategory), default=BillCategory.OTHER)
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[BillStatus] = mapped_column(str_enum(BillStatus), default=BillStatus.UPCOMING)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    frequency: Mapped[Frequency | None] = mapped_column(str_enum(Frequency))
    payment_method: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)


class PaymentPlan(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "payment_plans"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="total_non_negative"),
        CheckConstraint("completed_installments >= 0", name="completed_non_negative"),
    )

    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    total_amount: Mapped[Decimal] = mapped_column(Money)
    installment_amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    frequency: Mapped[Frequency] = mapped_column(str_enum(Frequency), default=Frequency.MONTHLY)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    next_payment_date: Mapped[date | None] = mapped_column(Date, index=True)
    remaining_amount: Mapped[Decimal] = mapped_column(Money)
    total_installments: Mapped[int] = mapped_column(Integer)
    completed_installments: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[PaymentPlanStatus] = mapped_column(str_enum(PaymentPlanStatus), default=PaymentPlanStatus.ACTIVE)


class Payment(UUIDPk, Timestamps, UserOwned, Base):
    """A record that a payment happened. Not a payment processor."""

    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_user_date", "user_id", "payment_date"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
    )

    bill_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bills.id", ondelete="SET NULL"), index=True)
    payment_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_plans.id", ondelete="SET NULL"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    payment_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[PaymentStatus] = mapped_column(str_enum(PaymentStatus), default=PaymentStatus.COMPLETED)
    notes: Mapped[str | None] = mapped_column(Text)

    bill: Mapped[Bill | None] = relationship(lazy="joined")


class Expense(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_user_date", "user_id", "expense_date"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
    )

    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[ExpenseCategory] = mapped_column(str_enum(ExpenseCategory), default=ExpenseCategory.OTHER)
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    expense_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[str | None] = mapped_column(String(100))


class Subscription(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_non_negative"),)

    name: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    billing_cycle: Mapped[Frequency] = mapped_column(str_enum(Frequency), default=Frequency.MONTHLY)
    next_billing_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(str_enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    notes: Mapped[str | None] = mapped_column(Text)


class Budget(UUIDPk, Timestamps, UserOwned, Base):
    """A monthly spending limit, for one expense category or (category NULL) for all spending."""

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_budgets_user_category"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("alert_threshold BETWEEN 1 AND 100", name="alert_threshold_range"),
    )

    category: Mapped[ExpenseCategory | None] = mapped_column(str_enum(ExpenseCategory))
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    # Percent of the limit at which the budget counts as "warning".
    alert_threshold: Mapped[int] = mapped_column(Integer, default=80, server_default="80")
