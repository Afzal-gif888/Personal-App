"""Academic and planning domain: subjects, tasks, study plans/sessions, events, reminders, goals."""

import datetime as dt
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UserOwned, UUIDPk, str_enum
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


class Subject(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("user_id", "code", name="uq_subjects_user_code"),)

    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(16))


class Task(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_user_status_due", "user_id", "status", "due_date"),
        Index("ix_tasks_user_category", "user_id", "category"),
    )

    subject_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[TaskCategory] = mapped_column(str_enum(TaskCategory), default=TaskCategory.GENERAL)
    priority: Mapped[Priority] = mapped_column(str_enum(Priority), default=Priority.MEDIUM)
    status: Mapped[TaskStatus] = mapped_column(str_enum(TaskStatus), default=TaskStatus.PENDING)
    due_date: Mapped[date | None] = mapped_column(Date)
    due_time: Mapped[time | None] = mapped_column(Time)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subject: Mapped[Subject | None] = relationship(lazy="joined")


class StudyPlan(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "study_plans"

    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[StudyPlanStatus] = mapped_column(str_enum(StudyPlanStatus), default=StudyPlanStatus.DRAFT)

    sessions: Mapped[list["StudySession"]] = relationship(
        back_populates="study_plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="(StudySession.date, StudySession.start_time)",
    )


class StudySession(UUIDPk, Timestamps, UserOwned, Base):
    """Sessions usually belong to a plan, but standalone sessions (plan_id NULL) are allowed."""

    __tablename__ = "study_sessions"
    __table_args__ = (Index("ix_study_sessions_user_date", "user_id", "date"),)

    study_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("study_plans.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), index=True)
    subject_name: Mapped[str | None] = mapped_column(String(200))
    topic: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    date: Mapped[dt.date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    priority: Mapped[Priority] = mapped_column(str_enum(Priority), default=Priority.MEDIUM)
    status: Mapped[StudySessionStatus] = mapped_column(
        str_enum(StudySessionStatus), default=StudySessionStatus.SCHEDULED
    )

    study_plan: Mapped[StudyPlan | None] = relationship(back_populates="sessions")
    subject: Mapped[Subject | None] = relationship(lazy="joined")


class Event(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_user_start", "user_id", "start_at"),)

    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[EventType] = mapped_column(str_enum(EventType), default=EventType.GENERAL)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(300))
    meeting_url: Mapped[str | None] = mapped_column(String(1024))
    notes: Mapped[str | None] = mapped_column(Text)


class Reminder(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "reminders"
    __table_args__ = (Index("ix_reminders_status_scheduled", "status", "scheduled_at"),)

    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[TaskCategory] = mapped_column(str_enum(TaskCategory), default=TaskCategory.GENERAL)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    repeat_rule: Mapped[RepeatRule] = mapped_column(str_enum(RepeatRule), default=RepeatRule.NONE)
    status: Mapped[ReminderStatus] = mapped_column(str_enum(ReminderStatus), default=ReminderStatus.PENDING)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Goal(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "goals"

    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[GoalCategory] = mapped_column(str_enum(GoalCategory), default=GoalCategory.GENERAL)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    unit: Mapped[str | None] = mapped_column(String(40))
    manual_progress: Mapped[int | None] = mapped_column()
    deadline: Mapped[date | None] = mapped_column(Date)
    status: Mapped[GoalStatus] = mapped_column(str_enum(GoalStatus), default=GoalStatus.ACTIVE)

    @property
    def progress(self) -> int:
        """0-100. Derived from current/target when both exist, otherwise the manually set value."""
        if self.status == GoalStatus.COMPLETED:
            return 100
        if self.target_value and self.current_value is not None and self.target_value > 0:
            return max(0, min(100, int(self.current_value / self.target_value * 100)))
        return self.manual_progress or 0
