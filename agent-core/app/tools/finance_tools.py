"""Finance tools - tracking and planning only.

None of these move money: there is no bank access, no card storage and no real payment
execution. `mark_bill_paid` records a payment the user already made elsewhere.
"""

from datetime import date, timedelta
from typing import Literal

from pydantic import Field

from app.backend.schemas import (
    Bill,
    BillPayment,
    Budget,
    Expense,
    ExpenseSummary,
    Payment,
    PaymentPlan,
    Subscription,
)
from app.schemas.tool import ToolDomain, ToolInput, ToolRisk
from app.tools.common import ID, Listing, listing
from app.tools.registry import ToolContext, ToolDefinition

Money = Field(gt=0, le=100_000_000, description="Amount in the user's currency")
Frequency = Literal["one_time", "weekly", "monthly", "quarterly", "half_yearly", "yearly"]
BillCategory = Literal[
    "electricity", "utilities", "internet", "phone", "rent", "hostel", "college_fees",
    "education", "subscription", "entertainment", "insurance", "other",
]
ExpenseCategory = Literal["food", "travel", "education", "shopping", "bills", "entertainment", "health", "other"]
OPEN_BILLS = ["upcoming", "due", "overdue"]


# --- bills ---


class GetBillsIn(ToolInput):
    include_paid: bool = False
    due_within_days: int | None = Field(default=None, ge=0, le=365, description="Only bills due in the next N days (overdue included)")


async def get_bills(ctx: ToolContext, args: GetBillsIn) -> Listing[Bill]:
    due_to = ctx.today + timedelta(days=args.due_within_days) if args.due_within_days is not None else None
    bills = await ctx.backend.list_bills(status=None if args.include_paid else OPEN_BILLS, due_to=due_to)
    return listing(bills)


class CreateBillIn(ToolInput):
    title: str = Field(min_length=1, max_length=300)
    amount: float = Money
    due_date: date
    category: BillCategory = "other"
    recurring: bool = False
    frequency: Frequency | None = None
    notes: str | None = Field(default=None, max_length=2000)


async def create_bill(ctx: ToolContext, args: CreateBillIn) -> Bill:
    return await ctx.backend.create_bill(args.to_backend())


class UpdateBillIn(ToolInput):
    bill_id: str = ID
    title: str | None = Field(default=None, min_length=1, max_length=300)
    amount: float | None = Field(default=None, gt=0, le=100_000_000)
    due_date: date | None = None
    category: BillCategory | None = None
    notes: str | None = Field(default=None, max_length=2000)


async def update_bill(ctx: ToolContext, args: UpdateBillIn) -> Bill:
    return await ctx.backend.update_bill(args.bill_id, args.to_backend(exclude={"bill_id"}))


class MarkBillPaidIn(ToolInput):
    bill_id: str = ID
    amount: float | None = Field(default=None, gt=0, le=100_000_000, description="Defaults to the bill amount")
    payment_date: date | None = Field(default=None, description="Defaults to today")
    payment_method: str | None = Field(default=None, max_length=100, description="Label only, e.g. 'UPI' - never card or account numbers")


async def mark_bill_paid(ctx: ToolContext, args: MarkBillPaidIn) -> BillPayment:
    return await ctx.backend.mark_bill_paid(args.bill_id, args.to_backend(exclude={"bill_id"}))


# --- payments & plans ---


class GetPaymentsIn(ToolInput):
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=25, ge=1, le=100)


async def get_payments(ctx: ToolContext, args: GetPaymentsIn) -> Listing[Payment]:
    page = await ctx.backend.list_payments(date_from=args.date_from, date_to=args.date_to, page_size=args.limit)
    return listing(page.items, page.total)


class GetPaymentPlansIn(ToolInput):
    status: Literal["active", "paused", "completed", "cancelled"] | None = "active"


async def get_payment_plans(ctx: ToolContext, args: GetPaymentPlansIn) -> Listing[PaymentPlan]:
    return listing(await ctx.backend.list_payment_plans(status=args.status))


class CreatePaymentPlanIn(ToolInput):
    title: str = Field(min_length=1, max_length=300)
    total_amount: float = Money
    installment_amount: float = Money
    frequency: Frequency = "monthly"
    start_date: date
    description: str | None = Field(default=None, max_length=2000)


async def create_payment_plan(ctx: ToolContext, args: CreatePaymentPlanIn) -> PaymentPlan:
    return await ctx.backend.create_payment_plan(args.to_backend())


# --- expenses ---


class GetExpensesIn(ToolInput):
    category: ExpenseCategory | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=25, ge=1, le=100)


async def get_expenses(ctx: ToolContext, args: GetExpensesIn) -> Listing[Expense]:
    page = await ctx.backend.list_expenses(
        category=args.category, date_from=args.date_from, date_to=args.date_to, page_size=args.limit
    )
    return listing(page.items, page.total)


class ExpenseSummaryIn(ToolInput):
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM; defaults to the current month")


async def get_expense_summary(ctx: ToolContext, args: ExpenseSummaryIn) -> ExpenseSummary:
    return await ctx.backend.expense_summary(args.month)


class CreateExpenseIn(ToolInput):
    title: str = Field(min_length=1, max_length=300)
    amount: float = Money
    category: ExpenseCategory = "other"
    expense_date: date | None = Field(default=None, description="Defaults to today")
    payment_method: str | None = Field(default=None, max_length=100)


async def create_expense(ctx: ToolContext, args: CreateExpenseIn) -> Expense:
    body = args.to_backend()
    body.setdefault("expenseDate", ctx.today.isoformat())
    return await ctx.backend.create_expense(body)


# --- subscriptions ---


class GetSubscriptionsIn(ToolInput):
    status: Literal["active", "paused", "cancelled"] | None = "active"
    renewing_within_days: int | None = Field(default=None, ge=0, le=365)


async def get_subscriptions(ctx: ToolContext, args: GetSubscriptionsIn) -> Listing[Subscription]:
    subs = await ctx.backend.list_subscriptions(status=args.status)
    if args.renewing_within_days is not None:
        cutoff = ctx.today + timedelta(days=args.renewing_within_days)
        subs = [x for x in subs if x.next_billing_date and x.next_billing_date <= cutoff]
    return listing(subs)


class CreateSubscriptionIn(ToolInput):
    name: str = Field(min_length=1, max_length=200)
    amount: float = Money
    billing_cycle: Frequency = "monthly"
    next_billing_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


async def create_subscription(ctx: ToolContext, args: CreateSubscriptionIn) -> Subscription:
    return await ctx.backend.create_subscription(args.to_backend())


class UpdateSubscriptionIn(ToolInput):
    subscription_id: str = ID
    amount: float | None = Field(default=None, gt=0, le=100_000_000)
    billing_cycle: Frequency | None = None
    next_billing_date: date | None = None
    status: Literal["active", "paused", "cancelled"] | None = None
    notes: str | None = Field(default=None, max_length=2000)


async def update_subscription(ctx: ToolContext, args: UpdateSubscriptionIn) -> Subscription:
    return await ctx.backend.update_subscription(args.subscription_id, args.to_backend(exclude={"subscription_id"}))


# --- budgets ---


class GetBudgetsIn(ToolInput):
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM; defaults to the current month")


async def get_budgets(ctx: ToolContext, args: GetBudgetsIn) -> Listing[Budget]:
    return listing(await ctx.backend.list_budgets(args.month))


class SetBudgetIn(ToolInput):
    amount: float = Money
    category: ExpenseCategory | None = Field(default=None, description="Omit for one overall monthly budget")
    alert_threshold: int = Field(default=80, ge=1, le=100, description="Warn at this percent of the budget")


async def set_budget(ctx: ToolContext, args: SetBudgetIn) -> Budget:
    """Create the monthly budget for a category, or update it if one already exists."""
    existing = next((b for b in await ctx.backend.list_budgets() if b.category == args.category), None)
    if existing:
        return await ctx.backend.update_budget(existing.id, {"amount": args.amount, "alertThreshold": args.alert_threshold})
    return await ctx.backend.create_budget(args.to_backend())


D, R, W = ToolDomain.FINANCE, ToolRisk.READ, ToolRisk.MUTATE

TOOLS = [
    ToolDefinition("get_bills", "List bills with amount, due date and status (upcoming, due, overdue, paid).", D, R, GetBillsIn, Listing[Bill], get_bills),
    ToolDefinition("create_bill", "Track a new bill. Tracking only - this never pays anything.", D, W, CreateBillIn, Bill, create_bill,
                   approval_reason="Adds a bill to track."),
    ToolDefinition("update_bill", "Edit a tracked bill.", D, W, UpdateBillIn, Bill, update_bill, approval_reason="Changes a tracked bill."),
    ToolDefinition("mark_bill_paid", "Record that the user already paid a bill (no money is moved). Recurring bills roll to the next period.",
                   D, W, MarkBillPaidIn, BillPayment, mark_bill_paid,
                   approval_reason="Records a payment against a bill. No money is transferred."),
    ToolDefinition("get_payments", "List recorded payments.", D, R, GetPaymentsIn, Listing[Payment], get_payments),
    ToolDefinition("get_payment_plans", "List installment/payment plans with remaining amounts.", D, R, GetPaymentPlansIn, Listing[PaymentPlan], get_payment_plans),
    ToolDefinition("create_payment_plan", "Track a new installment plan (e.g. fees paid monthly).", D, W, CreatePaymentPlanIn, PaymentPlan,
                   create_payment_plan, approval_reason="Adds a payment plan to track."),
    ToolDefinition("get_expenses", "List individual expenses.", D, R, GetExpensesIn, Listing[Expense], get_expenses),
    ToolDefinition("get_expense_summary", "Total spending for a month, broken down by category.", D, R, ExpenseSummaryIn, ExpenseSummary, get_expense_summary),
    ToolDefinition("create_expense", "Log an expense the user made.", D, W, CreateExpenseIn, Expense, create_expense,
                   approval_reason="Logs an expense."),
    ToolDefinition("get_subscriptions", "List subscriptions and when they renew.", D, R, GetSubscriptionsIn, Listing[Subscription], get_subscriptions),
    ToolDefinition("create_subscription", "Track a new subscription.", D, W, CreateSubscriptionIn, Subscription, create_subscription,
                   approval_reason="Adds a subscription to track."),
    ToolDefinition("update_subscription", "Change a subscription's price, cycle, renewal date or status (pause/cancel tracking).",
                   D, W, UpdateSubscriptionIn, Subscription, update_subscription, approval_reason="Changes a subscription."),
    ToolDefinition("get_budgets", "List monthly budgets with amount spent, remaining and status (on_track, warning, over).",
                   D, R, GetBudgetsIn, Listing[Budget], get_budgets),
    ToolDefinition("set_budget", "Set a monthly spending budget, overall or for one expense category (creates or updates it).",
                   D, W, SetBudgetIn, Budget, set_budget, approval_reason="Sets a monthly budget."),
]
