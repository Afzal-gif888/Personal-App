"""Tools the agent can call.

Read tools run immediately. Write tools never run during the agent loop: `propose()` validates the
input and builds a preview, which becomes an Approval; `apply()` runs only after the user approves.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, ClassVar, Generic, Literal, TypeVar
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.timeutils import as_utc, local_today, to_local
from app.llm import ToolSpec
from app.models import User
from app.models.enums import BillStatus, ExpenseCategory, GoalStatus, ReminderStatus, TaskStatus
from app.schemas.finance import BillPayIn, BudgetIn, BudgetUpdate, ExpenseIn
from app.schemas.planning import EventIn, ReminderIn, StudyPlanGenerateIn, StudyPlanIn, TaskIn
from app.services import budgets, documents, events, finance, goals, reminders, study, tasks

MAX_RANGE_DAYS = 62


@dataclass
class AgentContext:
    db: Session
    user: User
    tz: ZoneInfo

    @property
    def today(self) -> date:
        return local_today(self.tz)


@dataclass
class Proposal:
    action_label: str
    title: str
    description: str
    details: dict[str, Any]  # human-readable preview shown on the approval card
    payload: dict[str, Any]  # exactly what apply() will execute


class ToolInputError(Exception):
    """Invalid tool input. The message goes back to the model so it can correct itself."""


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


A = TypeVar("A", bound=Args)


class Tool(Generic[A]):
    name: ClassVar[str]
    description: ClassVar[str]
    args_model: type[A]
    requires_approval: ClassVar[bool] = False
    step_title: ClassVar[str]

    def spec(self) -> ToolSpec:
        schema = self.args_model.model_json_schema()
        schema.pop("title", None)
        for prop in schema.get("properties", {}).values():
            prop.pop("title", None)
        return ToolSpec(self.name, self.description, schema)

    def parse(self, raw: dict[str, Any]) -> A:
        try:
            return self.args_model.model_validate(raw or {})
        except ValidationError as exc:
            problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'input'}: {e['msg']}" for e in exc.errors())
            raise ToolInputError(f"Invalid input for {self.name}: {problems}")

    def run(self, ctx: AgentContext, args: A) -> dict[str, Any]:
        raise NotImplementedError

    def propose(self, ctx: AgentContext, args: A) -> Proposal:
        raise NotImplementedError

    def apply(self, ctx: AgentContext, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def _date_range(start: date, end: date) -> None:
    if end < start:
        raise ToolInputError("end_date must be on or after start_date")
    if (end - start).days > MAX_RANGE_DAYS:
        raise ToolInputError(f"Date range cannot exceed {MAX_RANGE_DAYS} days")


def _money(value: Decimal) -> float:
    return float(value)


def _task(t) -> dict:
    return {
        "id": str(t.id),
        "title": t.title,
        "status": t.status.value,
        "priority": t.priority.value,
        "category": t.category.value,
        "subject": t.subject.name if t.subject else None,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "due_time": t.due_time.strftime("%H:%M") if t.due_time else None,
    }


# --- Read tools -----------------------------------------------------------------------------------


class ListTasksArgs(Args):
    status: Literal["open", "completed", "all"] = "open"
    due_within_days: int | None = Field(default=None, ge=0, le=365, description="Only tasks due in the next N days")
    limit: int = Field(default=25, ge=1, le=100)


class ListTasks(Tool[ListTasksArgs]):
    name = "list_tasks"
    description = "List the user's tasks. Open tasks include pending and in-progress ones. Overdue tasks are included."
    args_model = ListTasksArgs
    step_title = "Checked tasks"

    def run(self, ctx, args: ListTasksArgs):
        status = {
            "open": [TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
            "completed": [TaskStatus.COMPLETED],
            "all": None,
        }[args.status]
        due_to = ctx.today + timedelta(days=args.due_within_days) if args.due_within_days is not None else None
        items, total = tasks.list_tasks(ctx.db, ctx.user, page=1, page_size=args.limit, status=status, due_to=due_to)
        return {"total": total, "tasks": [_task(t) for t in items]}


class ListCalendarArgs(Args):
    start_date: date
    end_date: date


class ListCalendar(Tool[ListCalendarArgs]):
    name = "list_calendar"
    description = "List calendar events and scheduled study sessions between two dates (inclusive, user's local time)."
    args_model = ListCalendarArgs
    step_title = "Checked calendar"

    def run(self, ctx, args: ListCalendarArgs):
        _date_range(args.start_date, args.end_date)
        evs = events.list_events(ctx.db, ctx.user, ctx.tz, start=args.start_date, end=args.end_date)
        sessions = study.list_sessions(ctx.db, ctx.user, start=args.start_date, end=args.end_date)
        return {
            "events": [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "type": e.event_type.value,
                    "start": to_local(as_utc(e.start_at), ctx.tz).isoformat(timespec="minutes"),
                    "end": to_local(as_utc(e.end_at), ctx.tz).isoformat(timespec="minutes") if e.end_at else None,
                    "location": e.location,
                }
                for e in evs
            ],
            "study_sessions": [
                {
                    "id": str(s.id),
                    "topic": s.topic,
                    "subject": s.subject_name,
                    "date": s.date.isoformat(),
                    "start_time": s.start_time.strftime("%H:%M"),
                    "end_time": s.end_time.strftime("%H:%M"),
                    "status": s.status.value,
                }
                for s in sessions
            ],
        }


class FindFreeSlotsArgs(Args):
    date: date
    duration_minutes: int = Field(default=60, ge=15, le=600)
    day_start: time = time(8, 0)
    day_end: time = time(22, 0)


class FindFreeSlots(Tool[FindFreeSlotsArgs]):
    name = "find_free_slots"
    description = "Find free time blocks on a given day that fit the requested duration, avoiding events and study sessions."
    args_model = FindFreeSlotsArgs
    step_title = "Looked for free time"

    def run(self, ctx, args: FindFreeSlotsArgs):
        if args.day_end <= args.day_start:
            raise ToolInputError("day_end must be after day_start")
        busy = study.busy_intervals(ctx.db, ctx.user, ctx.tz, args.date, args.date).get(args.date, [])
        need = timedelta(minutes=args.duration_minutes)
        slots = [
            {"start": s.strftime("%H:%M"), "end": e.strftime("%H:%M")}
            for s, e in study.free_slots(args.date, args.day_start, args.day_end, busy)
            if e - s >= need
        ]
        return {"date": args.date.isoformat(), "free_slots": slots}


class ListRemindersArgs(Args):
    include_completed: bool = False
    limit: int = Field(default=25, ge=1, le=100)


class ListReminders(Tool[ListRemindersArgs]):
    name = "list_reminders"
    description = "List the user's reminders, soonest first."
    args_model = ListRemindersArgs
    step_title = "Checked reminders"

    def run(self, ctx, args: ListRemindersArgs):
        status = None if args.include_completed else [ReminderStatus.PENDING, ReminderStatus.SNOOZED]
        items = reminders.list_reminders(ctx.db, ctx.user, status=status, limit=args.limit)
        return {
            "reminders": [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "at": to_local(as_utc(r.scheduled_at), ctx.tz).isoformat(timespec="minutes"),
                    "repeat": r.repeat_rule.value,
                    "status": r.status.value,
                }
                for r in items
            ]
        }


class ListBillsArgs(Args):
    include_paid: bool = False
    due_within_days: int | None = Field(default=None, ge=0, le=365)


class ListBills(Tool[ListBillsArgs]):
    name = "list_bills"
    description = "List the user's bills with amounts, due dates and status (upcoming, due, overdue, paid)."
    args_model = ListBillsArgs
    step_title = "Checked bills"

    def run(self, ctx, args: ListBillsArgs):
        status: list[BillStatus] | None = None if args.include_paid else list(finance.OPEN_BILL_STATUSES)
        due_to = ctx.today + timedelta(days=args.due_within_days) if args.due_within_days is not None else None
        bills = finance.list_bills(ctx.db, ctx.user, ctx.tz, status=status, due_to=due_to)
        return {
            "bills": [
                {
                    "id": str(b.id),
                    "title": b.title,
                    "amount": _money(b.amount),
                    "currency": b.currency,
                    "due_date": b.due_date.isoformat(),
                    "status": b.status.value,
                    "recurring": b.recurring,
                }
                for b in bills
            ]
        }


class SummarizeExpensesArgs(Args):
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM; defaults to this month")


class SummarizeExpenses(Tool[SummarizeExpensesArgs]):
    name = "summarize_expenses"
    description = "Total spending for a month, broken down by category."
    args_model = SummarizeExpensesArgs
    step_title = "Summarised spending"

    def run(self, ctx, args: SummarizeExpensesArgs):
        summary = finance.expense_summary(ctx.db, ctx.user, ctx.tz, args.month)
        return {
            **summary,
            "total": _money(summary["total"]),
            "by_category": [
                {"category": r["category"].value, "total": _money(r["total"]), "count": r["count"]}
                for r in summary["by_category"]
            ],
        }


class GetBudgetStatusArgs(Args):
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM; defaults to this month")


class GetBudgetStatus(Tool[GetBudgetStatusArgs]):
    name = "get_budget_status"
    description = (
        "The user's monthly budgets with spending so far: limit, spent, remaining, percent used and status "
        "(on_track, warning, over). A budget with category null covers all spending."
    )
    args_model = GetBudgetStatusArgs
    step_title = "Checked budgets"

    def run(self, ctx, args: GetBudgetStatusArgs):
        items = budgets.budgets_with_progress(ctx.db, ctx.user, ctx.tz, args.month)
        return {
            "month": items[0]["month"] if items else (args.month or f"{ctx.today:%Y-%m}"),
            "budgets": [
                {
                    "id": str(b["id"]),
                    "category": b["category"].value if b["category"] else None,
                    "limit": _money(b["amount"]),
                    "spent": _money(b["spent"]),
                    "remaining": _money(b["remaining"]),
                    "percent_used": b["percent_used"],
                    "status": b["status"],
                    "currency": b["currency"],
                }
                for b in items
            ],
        }


class ListGoalsArgs(Args):
    include_completed: bool = False


class ListGoals(Tool[ListGoalsArgs]):
    name = "list_goals"
    description = "List the user's goals with progress (0-100) and deadlines."
    args_model = ListGoalsArgs
    step_title = "Checked goals"

    def run(self, ctx, args: ListGoalsArgs):
        items = goals.list_goals(ctx.db, ctx.user, status=None if args.include_completed else GoalStatus.ACTIVE)
        return {
            "goals": [
                {
                    "id": str(g.id),
                    "title": g.title,
                    "category": g.category.value,
                    "progress": g.progress,
                    "current": _money(g.current_value) if g.current_value is not None else None,
                    "target": _money(g.target_value) if g.target_value is not None else None,
                    "unit": g.unit,
                    "deadline": g.deadline.isoformat() if g.deadline else None,
                    "status": g.status.value,
                }
                for g in items
            ]
        }


class ListDocumentsArgs(Args):
    query: str | None = Field(default=None, max_length=200, description="Filter by file name")
    limit: int = Field(default=10, ge=1, le=50)


class ListDocuments(Tool[ListDocumentsArgs]):
    name = "list_documents"
    description = "List the user's uploaded documents (names, categories, page counts). File contents are not available."
    args_model = ListDocumentsArgs
    step_title = "Checked documents"

    def run(self, ctx, args: ListDocumentsArgs):
        items, total = documents.list_documents(ctx.db, ctx.user, page=1, page_size=args.limit, q=args.query)
        return {
            "total": total,
            "documents": [
                {
                    "id": str(d.id),
                    "name": d.original_filename,
                    "category": d.category,
                    "pages": d.page_count,
                    "status": d.status.value,
                }
                for d in items
            ],
        }


# --- Write tools (approval required) --------------------------------------------------------------

Priority = Literal["low", "medium", "high"]
Category = Literal["academic", "personal", "financial", "career", "general"]


class CreateTaskArgs(Args):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    category: Category = "general"
    priority: Priority = "medium"
    due_date: date | None = None
    due_time: time | None = None
    subject: str | None = Field(default=None, max_length=200)


class CreateTask(Tool[CreateTaskArgs]):
    name = "create_task"
    description = "Propose a new task. The user must approve it before it is created."
    args_model = CreateTaskArgs
    requires_approval = True
    step_title = "Drafted a task"

    def propose(self, ctx, args: CreateTaskArgs):
        details = {"Title": args.title, "Priority": args.priority.title(), "Category": args.category.title()}
        if args.subject:
            details["Subject"] = args.subject
        if args.due_date:
            details["Due date"] = args.due_date.isoformat()
        if args.due_time:
            details["Due time"] = args.due_time.strftime("%H:%M")
        return Proposal("Create task", args.title, args.description or "New task", details, args.model_dump(mode="json"))

    def apply(self, ctx, payload):
        task = tasks.create_task(ctx.db, ctx.user, TaskIn.model_validate(payload), commit=False)
        return {"resource_type": "task", "resource_id": str(task.id), "summary": f"Created task “{task.title}”"}


class CompleteTaskArgs(Args):
    task_id: uuid.UUID


class CompleteTask(Tool[CompleteTaskArgs]):
    name = "complete_task"
    description = "Propose marking an existing task as completed (use an id from list_tasks)."
    args_model = CompleteTaskArgs
    requires_approval = True
    step_title = "Drafted a task update"

    def propose(self, ctx, args: CompleteTaskArgs):
        task = _lookup(lambda: tasks.get_task(ctx.db, ctx.user, args.task_id))
        if task.status == TaskStatus.COMPLETED:
            raise ToolInputError("That task is already completed")
        return Proposal(
            "Complete task", task.title, "Mark this task as completed", {"Task": task.title}, args.model_dump(mode="json")
        )

    def apply(self, ctx, payload):
        task = tasks.set_status(ctx.db, ctx.user, uuid.UUID(payload["task_id"]), TaskStatus.COMPLETED, commit=False)
        return {"resource_type": "task", "resource_id": str(task.id), "summary": f"Completed task “{task.title}”"}


class CreateReminderArgs(Args):
    title: str = Field(min_length=1, max_length=300)
    date: date
    time: time
    description: str | None = Field(default=None, max_length=2000)
    category: Category = "general"
    repeat_rule: Literal["none", "daily", "weekly", "monthly", "yearly"] = "none"


class CreateReminder(Tool[CreateReminderArgs]):
    name = "create_reminder"
    description = "Propose a reminder at a local date and time. The user must approve it before it is created."
    args_model = CreateReminderArgs
    requires_approval = True
    step_title = "Drafted a reminder"

    def propose(self, ctx, args: CreateReminderArgs):
        details = {"Title": args.title, "Date": args.date.isoformat(), "Time": args.time.strftime("%H:%M")}
        if args.repeat_rule != "none":
            details["Repeats"] = args.repeat_rule.title()
        details["Category"] = args.category.title()
        return Proposal(
            "Create reminder", args.title, args.description or "New reminder", details, args.model_dump(mode="json")
        )

    def apply(self, ctx, payload):
        r = reminders.create_reminder(ctx.db, ctx.user, ctx.tz, ReminderIn.model_validate(payload), commit=False)
        return {"resource_type": "reminder", "resource_id": str(r.id), "summary": f"Created reminder “{r.title}”"}


class CreateEventArgs(Args):
    title: str = Field(min_length=1, max_length=300)
    event_type: Literal[
        "class", "meeting", "project_meeting", "team_meeting", "interview", "appointment", "exam", "deadline",
        "personal", "general", "other",
    ] = "general"
    date: date
    start_time: time
    end_time: time | None = None
    location: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("end_time")
    @classmethod
    def _after(cls, value, info):
        start = info.data.get("start_time")
        if value and start and value <= start:
            raise ValueError("end_time must be after start_time")
        return value


class CreateEvent(Tool[CreateEventArgs]):
    name = "create_event"
    description = "Propose a calendar event at a local date and time. The user must approve it first."
    args_model = CreateEventArgs
    requires_approval = True
    step_title = "Drafted a calendar event"

    def propose(self, ctx, args: CreateEventArgs):
        when = args.start_time.strftime("%H:%M") + (f"–{args.end_time.strftime('%H:%M')}" if args.end_time else "")
        details = {"Title": args.title, "Type": args.event_type.replace("_", " ").title(), "Date": args.date.isoformat(), "Time": when}
        if args.location:
            details["Location"] = args.location
        return Proposal("Create event", args.title, args.description or "New calendar event", details, args.model_dump(mode="json"))

    def apply(self, ctx, payload):
        ev = events.create_event(ctx.db, ctx.user, ctx.tz, EventIn.model_validate(payload), commit=False)
        return {"resource_type": "event", "resource_id": str(ev.id), "summary": f"Added “{ev.title}” to the calendar"}


class CreateStudyPlanArgs(Args):
    subject: str = Field(min_length=1, max_length=200)
    topics: list[str] = Field(default_factory=list, max_length=30, description="Topics to rotate through, in order")
    start_date: date | None = Field(default=None, description="Defaults to tomorrow")
    days: int = Field(default=5, ge=1, le=30)
    minutes_per_day: int = Field(default=90, ge=15, le=480)
    session_minutes: int = Field(default=60, ge=15, le=180)


class CreateStudyPlan(Tool[CreateStudyPlanArgs]):
    name = "create_study_plan"
    description = (
        "Propose a study plan. Sessions are scheduled automatically inside the user's preferred study "
        "window, avoiding existing events and sessions. The user must approve the plan before it is saved."
    )
    args_model = CreateStudyPlanArgs
    requires_approval = True
    step_title = "Drafted a study plan"

    def propose(self, ctx, args: CreateStudyPlanArgs):
        plan = _lookup(lambda: study.build_plan(ctx.db, ctx.user, ctx.tz, StudyPlanGenerateIn(**args.model_dump())))
        hours = sum(
            (datetime.combine(s.date, s.end_time) - datetime.combine(s.date, s.start_time)).seconds for s in plan.sessions
        ) / 3600
        details = {
            "Subject": args.subject,
            "Sessions": len(plan.sessions),
            "Total hours": round(hours, 1),
            "Dates": f"{plan.start_date} to {plan.end_date}",
            "Schedule": [
                f"{s.date.isoformat()} {s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')} · {s.topic}"
                for s in plan.sessions
            ],
        }
        # The concrete sessions are frozen into the payload: what the user approves is what gets saved.
        return Proposal("Create study plan", plan.title, plan.description or "", details, plan.model_dump(mode="json"))

    def apply(self, ctx, payload):
        plan = study.create_plan(ctx.db, ctx.user, StudyPlanIn.model_validate(payload), commit=False)
        return {
            "resource_type": "study_plan",
            "resource_id": str(plan.id),
            "summary": f"Saved “{plan.title}” with {len(plan.sessions)} sessions",
        }


class LogExpenseArgs(Args):
    title: str = Field(min_length=1, max_length=300)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: Literal["food", "travel", "education", "shopping", "bills", "entertainment", "health", "other"] = "other"
    expense_date: date | None = Field(default=None, description="Defaults to today")
    description: str | None = Field(default=None, max_length=2000)


class LogExpense(Tool[LogExpenseArgs]):
    name = "log_expense"
    description = "Propose recording an expense in the user's currency. The user must approve it first."
    args_model = LogExpenseArgs
    requires_approval = True
    step_title = "Drafted an expense"

    def propose(self, ctx, args: LogExpenseArgs):
        payload = args.model_dump(mode="json")
        payload["expense_date"] = (args.expense_date or ctx.today).isoformat()
        currency = ctx.user.preferences.currency if ctx.user.preferences else "INR"
        details = {
            "Title": args.title,
            "Amount": f"{currency} {args.amount:,.2f}",
            "Category": args.category.title(),
            "Date": payload["expense_date"],
        }
        return Proposal("Log expense", args.title, args.description or "New expense", details, payload)

    def apply(self, ctx, payload):
        expense = finance.create_expense(ctx.db, ctx.user, ExpenseIn.model_validate(payload), commit=False)
        return {"resource_type": "expense", "resource_id": str(expense.id), "summary": f"Logged expense “{expense.title}”"}


class MarkBillPaidArgs(Args):
    bill_id: uuid.UUID
    payment_date: date | None = Field(default=None, description="Defaults to today")


class MarkBillPaid(Tool[MarkBillPaidArgs]):
    name = "mark_bill_paid"
    description = (
        "Propose recording that a bill was paid (use an id from list_bills). This only records the payment; "
        "no money is moved. The user must approve it first."
    )
    args_model = MarkBillPaidArgs
    requires_approval = True
    step_title = "Drafted a bill payment record"

    def propose(self, ctx, args: MarkBillPaidArgs):
        bill = _lookup(lambda: finance.get_bill(ctx.db, ctx.user, args.bill_id))
        if bill.status in (BillStatus.PAID, BillStatus.CANCELLED):
            raise ToolInputError(f"That bill is already {bill.status.value}")
        details = {
            "Bill": bill.title,
            "Amount": f"{bill.currency} {bill.amount:,.2f}",
            "Due date": bill.due_date.isoformat(),
            "Paid on": (args.payment_date or ctx.today).isoformat(),
        }
        return Proposal("Mark bill paid", bill.title, "Record this bill as paid", details, args.model_dump(mode="json"))

    def apply(self, ctx, payload):
        pay = BillPayIn(payment_date=payload.get("payment_date"))
        bill, _, next_bill = finance.pay_bill(ctx.db, ctx.user, ctx.tz, uuid.UUID(payload["bill_id"]), pay, commit=False)
        summary = f"Marked “{bill.title}” as paid"
        if next_bill:
            summary += f"; next bill due {next_bill.due_date.isoformat()}"
        return {"resource_type": "bill", "resource_id": str(bill.id), "summary": summary}


class SetBudgetArgs(Args):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, description="Monthly limit in the user's currency")
    category: Literal["food", "travel", "education", "shopping", "bills", "entertainment", "health", "other"] | None = Field(
        default=None, description="Expense category; omit for one overall budget covering all spending"
    )
    alert_threshold: int = Field(default=80, ge=1, le=100, description="Warn at this percent of the limit")


class SetBudget(Tool[SetBudgetArgs]):
    name = "set_budget"
    description = (
        "Propose creating or changing a monthly budget (spending limit) for an expense category or for all "
        "spending. Replaces the existing limit for that category. The user must approve it first."
    )
    args_model = SetBudgetArgs
    requires_approval = True
    step_title = "Drafted a budget"

    def propose(self, ctx, args: SetBudgetArgs):
        existing = budgets.find_budget(ctx.db, ctx.user, ExpenseCategory(args.category) if args.category else None)
        currency = existing.currency if existing else (ctx.user.preferences.currency if ctx.user.preferences else "INR")
        label = args.category.title() if args.category else "Overall"
        details = {
            "Category": label,
            "Monthly limit": f"{currency} {args.amount:,.2f}",
            "Alert at": f"{args.alert_threshold}%",
        }
        if existing:
            details["Current limit"] = f"{existing.currency} {existing.amount:,.2f}"
        title = f"{label} budget"
        return Proposal(
            "Update budget" if existing else "Set budget",
            title,
            f"{'Change' if existing else 'Set'} the monthly {label.lower()} budget",
            details,
            args.model_dump(mode="json"),
        )

    def apply(self, ctx, payload):
        category = ExpenseCategory(payload["category"]) if payload.get("category") else None
        existing = budgets.find_budget(ctx.db, ctx.user, category)
        if existing:
            data = BudgetUpdate(amount=payload["amount"], alert_threshold=payload["alert_threshold"])
            budget = budgets.update_budget(ctx.db, ctx.user, existing.id, data, commit=False)
        else:
            data = BudgetIn(category=category, amount=payload["amount"], alert_threshold=payload["alert_threshold"])
            budget = budgets.create_budget(ctx.db, ctx.user, data, commit=False)
        label = category.value if category else "overall"
        return {
            "resource_type": "budget",
            "resource_id": str(budget.id),
            "summary": f"Set the {label} budget to {budget.currency} {budget.amount:,.2f} a month",
        }


def _lookup(fn):
    """Turn domain errors (not found, no free slots, ...) into input errors the model can react to."""
    try:
        return fn()
    except AppError as exc:
        raise ToolInputError(exc.message)


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in (
        ListTasks(),
        ListCalendar(),
        FindFreeSlots(),
        ListReminders(),
        ListBills(),
        SummarizeExpenses(),
        GetBudgetStatus(),
        ListGoals(),
        ListDocuments(),
        CreateTask(),
        CompleteTask(),
        CreateReminder(),
        CreateEvent(),
        CreateStudyPlan(),
        LogExpense(),
        MarkBillPaid(),
        SetBudget(),
    )
}


def tool_specs() -> list[ToolSpec]:
    return [t.spec() for t in TOOLS.values()]
