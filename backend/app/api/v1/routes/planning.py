"""Subjects, tasks, study plans/sessions, events, reminders and goals."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DB, CurrentUser, Paging, UserZone
from app.models.enums import (
    EventType,
    GoalCategory,
    GoalStatus,
    Priority,
    ReminderStatus,
    StudyPlanStatus,
    StudySessionStatus,
    TaskCategory,
    TaskStatus,
)
from app.schemas.common import Page
from app.schemas.planning import (
    EventIn,
    EventOut,
    EventUpdate,
    GoalIn,
    GoalOut,
    GoalUpdate,
    ReminderIn,
    ReminderOut,
    ReminderUpdate,
    SnoozeIn,
    StudyPlanGenerateIn,
    StudyPlanIn,
    StudyPlanOut,
    StudyPlanUpdate,
    StudySessionIn,
    StudySessionOut,
    StudySessionUpdate,
    SubjectIn,
    SubjectOut,
    SubjectUpdate,
    TaskIn,
    TaskOut,
    TaskUpdate,
)
from app.services import events, goals, reminders, study, subjects, tasks

router = APIRouter()

# --- Subjects -------------------------------------------------------------------------------------


@router.get("/subjects", response_model=list[SubjectOut], tags=["subjects"])
def list_subjects(user: CurrentUser, db: DB):
    return subjects.list_subjects(db, user)


@router.post("/subjects", response_model=SubjectOut, status_code=201, tags=["subjects"])
def create_subject(data: SubjectIn, user: CurrentUser, db: DB):
    return subjects.create_subject(db, user, data)


@router.patch("/subjects/{subject_id}", response_model=SubjectOut, tags=["subjects"])
def update_subject(subject_id: uuid.UUID, data: SubjectUpdate, user: CurrentUser, db: DB):
    return subjects.update_subject(db, user, subject_id, data)


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["subjects"])
def delete_subject(subject_id: uuid.UUID, user: CurrentUser, db: DB):
    subjects.delete_subject(db, user, subject_id)


# --- Tasks ----------------------------------------------------------------------------------------


@router.get("/tasks", response_model=Page[TaskOut], tags=["tasks"])
def list_tasks(
    user: CurrentUser,
    db: DB,
    paging: Paging,
    task_status: Annotated[list[TaskStatus] | None, Query(alias="status")] = None,
    category: TaskCategory | None = None,
    priority: Priority | None = None,
    subject_id: uuid.UUID | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
):
    items, total = tasks.list_tasks(
        db, user, page=paging.page, page_size=paging.page_size, status=task_status, category=category,
        priority=priority, subject_id=subject_id, due_from=due_from, due_to=due_to, q=q,
    )
    return Page(items=[TaskOut.from_model(t) for t in items], total=total, page=paging.page, page_size=paging.page_size)


@router.post("/tasks", response_model=TaskOut, status_code=201, tags=["tasks"])
def create_task(data: TaskIn, user: CurrentUser, db: DB):
    return TaskOut.from_model(tasks.create_task(db, user, data))


@router.get("/tasks/{task_id}", response_model=TaskOut, tags=["tasks"])
def get_task(task_id: uuid.UUID, user: CurrentUser, db: DB):
    return TaskOut.from_model(tasks.get_task(db, user, task_id))


@router.patch("/tasks/{task_id}", response_model=TaskOut, tags=["tasks"])
def update_task(task_id: uuid.UUID, data: TaskUpdate, user: CurrentUser, db: DB):
    return TaskOut.from_model(tasks.update_task(db, user, task_id, data))


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
def delete_task(task_id: uuid.UUID, user: CurrentUser, db: DB):
    tasks.delete_task(db, user, task_id)


# --- Study plans & sessions -----------------------------------------------------------------------


@router.get("/study-plans", response_model=list[StudyPlanOut], tags=["study"])
def list_study_plans(user: CurrentUser, db: DB, plan_status: Annotated[StudyPlanStatus | None, Query(alias="status")] = None):
    return [StudyPlanOut.from_model(p) for p in study.list_plans(db, user, status=plan_status)]


@router.post("/study-plans", response_model=StudyPlanOut, status_code=201, tags=["study"])
def create_study_plan(data: StudyPlanIn, user: CurrentUser, db: DB):
    return StudyPlanOut.from_model(study.create_plan(db, user, data))


@router.post("/study-plans/generate", response_model=StudyPlanIn, tags=["study"])
def generate_study_plan(data: StudyPlanGenerateIn, user: CurrentUser, db: DB, tz: UserZone):
    """Draft a plan that fits the user's study window and free time. Nothing is saved: POST the
    returned body (optionally edited) to /study-plans to keep it."""
    return study.build_plan(db, user, tz, data)


@router.get("/study-plans/{plan_id}", response_model=StudyPlanOut, tags=["study"])
def get_study_plan(plan_id: uuid.UUID, user: CurrentUser, db: DB):
    return StudyPlanOut.from_model(study.get_plan(db, user, plan_id))


@router.patch("/study-plans/{plan_id}", response_model=StudyPlanOut, tags=["study"])
def update_study_plan(plan_id: uuid.UUID, data: StudyPlanUpdate, user: CurrentUser, db: DB):
    return StudyPlanOut.from_model(study.update_plan(db, user, plan_id, data))


@router.delete("/study-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["study"])
def delete_study_plan(plan_id: uuid.UUID, user: CurrentUser, db: DB):
    study.delete_plan(db, user, plan_id)


@router.get("/study-sessions", response_model=list[StudySessionOut], tags=["study"])
def list_study_sessions(
    user: CurrentUser,
    db: DB,
    start: date | None = None,
    end: date | None = None,
    session_status: Annotated[StudySessionStatus | None, Query(alias="status")] = None,
    plan_id: uuid.UUID | None = None,
):
    items = study.list_sessions(db, user, start=start, end=end, status=session_status, plan_id=plan_id)
    return [StudySessionOut.from_model(s) for s in items]


@router.post("/study-sessions", response_model=StudySessionOut, status_code=201, tags=["study"])
def create_study_session(data: StudySessionIn, user: CurrentUser, db: DB):
    return StudySessionOut.from_model(study.create_session(db, user, data))


@router.patch("/study-sessions/{session_id}", response_model=StudySessionOut, tags=["study"])
def update_study_session(session_id: uuid.UUID, data: StudySessionUpdate, user: CurrentUser, db: DB):
    return StudySessionOut.from_model(study.update_session(db, user, session_id, data))


@router.delete("/study-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["study"])
def delete_study_session(session_id: uuid.UUID, user: CurrentUser, db: DB):
    study.delete_session(db, user, session_id)


# --- Events ---------------------------------------------------------------------------------------


@router.get("/events", response_model=list[EventOut], tags=["events"])
def list_events(
    user: CurrentUser,
    db: DB,
    tz: UserZone,
    start: date | None = None,
    end: date | None = None,
    event_type: EventType | None = None,
):
    return [EventOut.from_model(e, tz) for e in events.list_events(db, user, tz, start=start, end=end, event_type=event_type)]


@router.post("/events", response_model=EventOut, status_code=201, tags=["events"])
def create_event(data: EventIn, user: CurrentUser, db: DB, tz: UserZone):
    return EventOut.from_model(events.create_event(db, user, tz, data), tz)


@router.get("/events/{event_id}", response_model=EventOut, tags=["events"])
def get_event(event_id: uuid.UUID, user: CurrentUser, db: DB, tz: UserZone):
    return EventOut.from_model(events.get_event(db, user, event_id), tz)


@router.patch("/events/{event_id}", response_model=EventOut, tags=["events"])
def update_event(event_id: uuid.UUID, data: EventUpdate, user: CurrentUser, db: DB, tz: UserZone):
    return EventOut.from_model(events.update_event(db, user, tz, event_id, data), tz)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["events"])
def delete_event(event_id: uuid.UUID, user: CurrentUser, db: DB):
    events.delete_event(db, user, event_id)


# --- Reminders ------------------------------------------------------------------------------------


@router.get("/reminders", response_model=list[ReminderOut], tags=["reminders"])
def list_reminders(
    user: CurrentUser,
    db: DB,
    tz: UserZone,
    reminder_status: Annotated[list[ReminderStatus] | None, Query(alias="status")] = None,
):
    return [ReminderOut.from_model(r, tz) for r in reminders.list_reminders(db, user, status=reminder_status)]


@router.post("/reminders", response_model=ReminderOut, status_code=201, tags=["reminders"])
def create_reminder(data: ReminderIn, user: CurrentUser, db: DB, tz: UserZone):
    return ReminderOut.from_model(reminders.create_reminder(db, user, tz, data), tz)


@router.patch("/reminders/{reminder_id}", response_model=ReminderOut, tags=["reminders"])
def update_reminder(reminder_id: uuid.UUID, data: ReminderUpdate, user: CurrentUser, db: DB, tz: UserZone):
    return ReminderOut.from_model(reminders.update_reminder(db, user, tz, reminder_id, data), tz)


@router.post("/reminders/{reminder_id}/complete", response_model=ReminderOut, tags=["reminders"])
def complete_reminder(reminder_id: uuid.UUID, user: CurrentUser, db: DB, tz: UserZone):
    """Completes a one-off reminder; a repeating one moves to its next occurrence."""
    return ReminderOut.from_model(reminders.complete_reminder(db, user, reminder_id), tz)


@router.post("/reminders/{reminder_id}/snooze", response_model=ReminderOut, tags=["reminders"])
def snooze_reminder(reminder_id: uuid.UUID, user: CurrentUser, db: DB, tz: UserZone, data: SnoozeIn | None = None):
    minutes = data.minutes if data else SnoozeIn().minutes
    return ReminderOut.from_model(reminders.snooze_reminder(db, user, reminder_id, minutes), tz)


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["reminders"])
def delete_reminder(reminder_id: uuid.UUID, user: CurrentUser, db: DB):
    reminders.delete_reminder(db, user, reminder_id)


# --- Goals ----------------------------------------------------------------------------------------


@router.get("/goals", response_model=list[GoalOut], tags=["goals"])
def list_goals(
    user: CurrentUser,
    db: DB,
    goal_status: Annotated[GoalStatus | None, Query(alias="status")] = None,
    category: GoalCategory | None = None,
):
    return [GoalOut.from_model(g) for g in goals.list_goals(db, user, status=goal_status, category=category)]


@router.post("/goals", response_model=GoalOut, status_code=201, tags=["goals"])
def create_goal(data: GoalIn, user: CurrentUser, db: DB):
    return GoalOut.from_model(goals.create_goal(db, user, data))


@router.patch("/goals/{goal_id}", response_model=GoalOut, tags=["goals"])
def update_goal(goal_id: uuid.UUID, data: GoalUpdate, user: CurrentUser, db: DB):
    return GoalOut.from_model(goals.update_goal(db, user, goal_id, data))


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["goals"])
def delete_goal(goal_id: uuid.UUID, user: CurrentUser, db: DB):
    goals.delete_goal(db, user, goal_id)
