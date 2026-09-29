"""Typed views of backend responses (camelCase on the wire, snake_case here).

Only the fields the agent uses are declared; unknown fields are ignored so backend additions
never break the Agent Core.
"""

from datetime import date, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class BackendModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class Page(BackendModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 50


class UserProfile(BackendModel):
    id: str
    name: str = ""
    email: str = ""
    university: str | None = None
    major: str | None = None


class Preferences(BackendModel):
    daily_study_goal_minutes: int | None = None
    preferred_study_start: str | None = None
    preferred_study_end: str | None = None
    default_reminder_time: str | None = None
    timezone: str = "UTC"
    currency: str = "INR"


class ConversationMessage(BackendModel):
    role: str
    content: str


class Subject(BackendModel):
    id: str
    name: str
    code: str | None = None
    description: str | None = None


class Task(BackendModel):
    id: str
    title: str
    description: str | None = None
    category: str
    priority: str
    status: str
    due_date: date | None = None
    due_time: str | None = None
    subject: str | None = None
    completed_at: datetime | None = None


class StudySession(BackendModel):
    id: str
    study_plan_id: str | None = None
    subject_name: str | None = None
    topic: str
    date: date
    start_time: str
    end_time: str
    priority: str = "medium"
    status: str


class StudyPlan(BackendModel):
    id: str
    title: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str
    sessions: list[StudySession] = Field(default_factory=list)


class StudyPlanDraft(BackendModel):
    """Output of POST /study-plans/generate: a plan that has not been saved."""

    title: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    sessions: list[dict[str, Any]] = Field(default_factory=list)


class Event(BackendModel):
    id: str
    title: str
    description: str | None = None
    event_type: str
    start_at: datetime
    end_at: datetime | None = None
    date: date
    start_time: str
    end_time: str | None = None
    location: str | None = None
    meeting_url: str | None = None


class Reminder(BackendModel):
    id: str
    title: str
    description: str | None = None
    category: str
    scheduled_at: datetime
    date: date
    time: str
    repeat_rule: str
    status: str


class Bill(BackendModel):
    id: str
    title: str
    category: str
    amount: float
    currency: str
    due_date: date
    status: str
    recurring: bool = False
    frequency: str | None = None


class Payment(BackendModel):
    id: str
    bill_id: str | None = None
    payment_plan_id: str | None = None
    amount: float
    currency: str
    payment_date: date
    status: str


class BillPayment(BackendModel):
    bill: Bill
    payment: Payment
    next_bill: Bill | None = None


class PaymentPlan(BackendModel):
    id: str
    title: str
    total_amount: float
    installment_amount: float
    currency: str
    frequency: str
    next_payment_date: date | None = None
    remaining_amount: float
    total_installments: int
    completed_installments: int
    status: str


class Expense(BackendModel):
    id: str
    title: str
    category: str
    amount: float
    currency: str
    expense_date: date


class CategoryTotal(BackendModel):
    category: str
    total: float
    count: int


class ExpenseSummary(BackendModel):
    month: str
    currency: str
    total: float
    count: int
    by_category: list[CategoryTotal] = Field(default_factory=list)


class Subscription(BackendModel):
    id: str
    name: str
    amount: float
    currency: str
    billing_cycle: str
    next_billing_date: date | None = None
    status: str


class Budget(BackendModel):
    id: str
    category: str | None = None  # None = one overall budget for all spending
    amount: float
    currency: str
    alert_threshold: int
    month: str
    spent: float
    remaining: float
    percent_used: int
    status: str  # on_track | warning | over


class Goal(BackendModel):
    id: str
    title: str
    description: str | None = None
    category: str
    target_value: float | None = None
    current_value: float | None = None
    unit: str | None = None
    progress: int = 0
    deadline: date | None = None
    status: str


class Document(BackendModel):
    id: str
    name: str
    mime_type: str
    size: int
    category: str | None = None
    status: str
    page_count: int | None = None
    processed_at: datetime | None = None
