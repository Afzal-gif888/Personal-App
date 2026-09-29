import uuid
from datetime import date as Date, datetime as DateTime, time as Time
from decimal import Decimal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from app.core.timeutils import to_local
from app.models import Event, Goal, Reminder, StudySession, Task
from app.models.enums import (
    EventType,
    GoalCategory,
    GoalStatus,
    Priority,
    ReminderStatus,
    RepeatRule,
    StudyPlanStatus,
    StudySessionStatus,
    TaskCategory,
    TaskStatus,
)
from app.schemas.common import HHMM, APIModel, InputModel, Money, UTCDateTime

Title = Field(min_length=1, max_length=300)
LongText = Field(default=None, max_length=10_000)


# --- Subjects -------------------------------------------------------------------------------------


class SubjectIn(InputModel):
    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = LongText
    color: str | None = Field(default=None, max_length=16)


class SubjectUpdate(InputModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = LongText
    color: str | None = Field(default=None, max_length=16)


class SubjectOut(APIModel):
    id: uuid.UUID
    name: str
    code: str | None
    description: str | None
    color: str | None
    created_at: UTCDateTime


# --- Tasks ----------------------------------------------------------------------------------------


class TaskIn(InputModel):
    title: str = Title
    description: str | None = LongText
    category: TaskCategory = TaskCategory.GENERAL
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    due_date: Date | None = None
    due_time: Time | None = None
    subject_id: uuid.UUID | None = None
    # Convenience: a subject name is matched (case-insensitively) or created. Ignored if subjectId is set.
    subject: str | None = Field(default=None, max_length=200)


class TaskUpdate(InputModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = LongText
    category: TaskCategory | None = None
    priority: Priority | None = None
    status: TaskStatus | None = None
    due_date: Date | None = None
    due_time: Time | None = None
    subject_id: uuid.UUID | None = None
    subject: str | None = Field(default=None, max_length=200)


class TaskOut(APIModel):
    id: uuid.UUID
    title: str
    description: str | None
    category: TaskCategory
    priority: Priority
    status: TaskStatus
    due_date: Date | None
    due_time: HHMM | None
    subject_id: uuid.UUID | None
    subject: str | None
    completed_at: UTCDateTime | None
    created_at: UTCDateTime
    updated_at: UTCDateTime

    @classmethod
    def from_model(cls, task: Task) -> "TaskOut":
        return cls.model_validate(
            {**_columns(task), "subject": task.subject.name if task.subject else None}
        )


# --- Study plans & sessions -----------------------------------------------------------------------


class StudySessionIn(InputModel):
    topic: str = Title
    description: str | None = LongText
    date: Date
    start_time: Time
    end_time: Time
    priority: Priority = Priority.MEDIUM
    status: StudySessionStatus = StudySessionStatus.SCHEDULED
    subject_id: uuid.UUID | None = None
    subject_name: str | None = Field(default=None, max_length=200)
    study_plan_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _times(self):
        if self.end_time <= self.start_time:
            raise ValueError("endTime must be after startTime")
        return self


class StudySessionUpdate(InputModel):
    topic: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = LongText
    date: Date | None = None
    start_time: Time | None = None
    end_time: Time | None = None
    priority: Priority | None = None
    status: StudySessionStatus | None = None
    subject_id: uuid.UUID | None = None
    subject_name: str | None = Field(default=None, max_length=200)


class StudySessionOut(APIModel):
    id: uuid.UUID
    study_plan_id: uuid.UUID | None
    subject_id: uuid.UUID | None
    subject_name: str | None
    topic: str
    description: str | None
    date: Date
    start_time: HHMM
    end_time: HHMM
    priority: Priority
    status: StudySessionStatus
    created_at: UTCDateTime

    @classmethod
    def from_model(cls, s: StudySession) -> "StudySessionOut":
        name = s.subject_name or (s.subject.name if s.subject else None)
        return cls.model_validate({**_columns(s), "subject_name": name})


class PlanSessionIn(InputModel):
    topic: str = Title
    description: str | None = LongText
    date: Date
    start_time: Time
    end_time: Time
    priority: Priority = Priority.MEDIUM
    subject_name: str | None = Field(default=None, max_length=200)


class StudyPlanIn(InputModel):
    title: str = Title
    description: str | None = LongText
    start_date: Date | None = None
    end_date: Date | None = None
    status: StudyPlanStatus = StudyPlanStatus.ACTIVE
    sessions: list[PlanSessionIn] = Field(default_factory=list, max_length=200)


class StudyPlanUpdate(InputModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = LongText
    start_date: Date | None = None
    end_date: Date | None = None
    status: StudyPlanStatus | None = None


class StudyPlanGenerateIn(InputModel):
    subject: str = Field(min_length=1, max_length=200)
    topics: list[str] = Field(default_factory=list, max_length=50)
    start_date: Date | None = None
    days: int = Field(default=5, ge=1, le=60)
    minutes_per_day: int = Field(default=90, ge=15, le=600)
    session_minutes: int = Field(default=60, ge=15, le=240)


class StudyPlanOut(APIModel):
    id: uuid.UUID
    title: str
    description: str | None
    start_date: Date | None
    end_date: Date | None
    status: StudyPlanStatus
    sessions: list[StudySessionOut]
    created_at: UTCDateTime
    updated_at: UTCDateTime

    @classmethod
    def from_model(cls, plan) -> "StudyPlanOut":
        return cls.model_validate(
            {**_columns(plan), "sessions": [StudySessionOut.from_model(s) for s in plan.sessions]}
        )


# --- Events ---------------------------------------------------------------------------------------


class _LocalSchedule(InputModel):
    """Accepts either absolute datetimes or a local date + time pair (interpreted in the user's timezone)."""

    @staticmethod
    def _combine(d: Date | None, t: Time | None) -> DateTime | None:
        return DateTime.combine(d, t) if d and t else None


class EventIn(_LocalSchedule):
    title: str = Title
    description: str | None = LongText
    event_type: EventType = EventType.GENERAL
    start_at: DateTime | None = None
    end_at: DateTime | None = None
    date: Date | None = None
    start_time: Time | None = None
    end_time: Time | None = None
    location: str | None = Field(default=None, max_length=300)
    meeting_url: str | None = Field(default=None, max_length=1024)
    notes: str | None = LongText

    @model_validator(mode="after")
    def _resolve(self):
        self.start_at = self.start_at or self._combine(self.date, self.start_time)
        self.end_at = self.end_at or self._combine(self.date, self.end_time)
        if self.start_at is None:
            raise ValueError("Provide startAt, or date and startTime")
        return self


class EventUpdate(_LocalSchedule):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = LongText
    event_type: EventType | None = None
    start_at: DateTime | None = None
    end_at: DateTime | None = None
    date: Date | None = None
    start_time: Time | None = None
    end_time: Time | None = None
    location: str | None = Field(default=None, max_length=300)
    meeting_url: str | None = Field(default=None, max_length=1024)
    notes: str | None = LongText


class EventOut(APIModel):
    id: uuid.UUID
    title: str
    description: str | None
    event_type: EventType
    start_at: DateTime
    end_at: DateTime | None
    date: Date
    start_time: HHMM
    end_time: HHMM | None
    location: str | None
    meeting_url: str | None
    notes: str | None
    created_at: UTCDateTime

    @classmethod
    def from_model(cls, ev: Event, tz: ZoneInfo) -> "EventOut":
        start, end = to_local(ev.start_at, tz), to_local(ev.end_at, tz)
        return cls.model_validate(
            {
                **_columns(ev),
                "start_at": start,
                "end_at": end,
                "date": start.date(),
                "start_time": start.time(),
                "end_time": end.time() if end else None,
            }
        )


# --- Reminders ------------------------------------------------------------------------------------


class ReminderIn(_LocalSchedule):
    title: str = Title
    description: str | None = LongText
    category: TaskCategory = TaskCategory.GENERAL
    scheduled_at: DateTime | None = None
    date: Date | None = None
    time: Time | None = None
    repeat_rule: RepeatRule = RepeatRule.NONE

    @model_validator(mode="after")
    def _resolve(self):
        self.scheduled_at = self.scheduled_at or self._combine(self.date, self.time)
        if self.scheduled_at is None:
            raise ValueError("Provide scheduledAt, or date and time")
        return self


class ReminderUpdate(_LocalSchedule):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = LongText
    category: TaskCategory | None = None
    scheduled_at: DateTime | None = None
    date: Date | None = None
    time: Time | None = None
    repeat_rule: RepeatRule | None = None
    status: ReminderStatus | None = None


class SnoozeIn(InputModel):
    minutes: int = Field(default=30, ge=1, le=7 * 24 * 60)


class ReminderOut(APIModel):
    id: uuid.UUID
    title: str
    description: str | None
    category: TaskCategory
    scheduled_at: DateTime
    date: Date
    time: HHMM
    repeat_rule: RepeatRule
    status: ReminderStatus
    completed_at: UTCDateTime | None
    created_at: UTCDateTime

    @classmethod
    def from_model(cls, r: Reminder, tz: ZoneInfo) -> "ReminderOut":
        at = to_local(r.scheduled_at, tz)
        return cls.model_validate({**_columns(r), "scheduled_at": at, "date": at.date(), "time": at.time()})


# --- Goals ----------------------------------------------------------------------------------------


class GoalIn(InputModel):
    title: str = Title
    description: str | None = LongText
    category: GoalCategory = GoalCategory.GENERAL
    target_value: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    current_value: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    unit: str | None = Field(default=None, max_length=40)
    manual_progress: int | None = Field(default=None, ge=0, le=100)
    deadline: Date | None = None
    status: GoalStatus = GoalStatus.ACTIVE


class GoalUpdate(InputModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = LongText
    category: GoalCategory | None = None
    target_value: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    current_value: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    unit: str | None = Field(default=None, max_length=40)
    manual_progress: int | None = Field(default=None, ge=0, le=100)
    deadline: Date | None = None
    status: GoalStatus | None = None


class GoalOut(APIModel):
    id: uuid.UUID
    title: str
    description: str | None
    category: GoalCategory
    target_value: Money | None
    current_value: Money | None
    unit: str | None
    manual_progress: int | None
    progress: int
    deadline: Date | None
    status: GoalStatus
    created_at: UTCDateTime
    updated_at: UTCDateTime

    @classmethod
    def from_model(cls, g: Goal) -> "GoalOut":
        return cls.model_validate({**_columns(g), "progress": g.progress})


def _columns(obj) -> dict:
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns}
