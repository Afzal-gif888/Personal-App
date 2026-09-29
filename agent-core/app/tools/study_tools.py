"""Study tools: subjects, study plans and study sessions."""

import datetime as dt
from datetime import timedelta
from typing import Literal

from pydantic import Field, model_validator

from app.backend.schemas import StudyPlan, StudySession, Subject
from app.schemas.tool import HHMM, NoInput, ToolDomain, ToolInput, ToolRisk
from app.tools.common import ID, Listing, listing
from app.tools.registry import ToolContext, ToolDefinition, ToolError


async def get_subjects(ctx: ToolContext, args: NoInput) -> Listing[Subject]:
    return listing(await ctx.backend.list_subjects())


class CreateSubjectIn(ToolInput):
    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=50, description="Course code, e.g. CS229")
    description: str | None = Field(default=None, max_length=2000)


async def create_subject(ctx: ToolContext, args: CreateSubjectIn) -> Subject:
    return await ctx.backend.create_subject(args.to_backend())


class GetStudyPlanIn(ToolInput):
    plan_id: str | None = Field(default=None, max_length=64, description="Omit to list plans")
    status: Literal["draft", "active", "completed", "archived"] | None = Field(default=None, description="Filter when listing")


async def get_study_plan(ctx: ToolContext, args: GetStudyPlanIn) -> Listing[StudyPlan]:
    if args.plan_id:
        return listing([await ctx.backend.get_study_plan(args.plan_id)])
    return listing(await ctx.backend.list_study_plans(status=args.status))


class GetStudySessionsIn(ToolInput):
    start_date: dt.date | None = Field(default=None, description="Defaults to today")
    end_date: dt.date | None = Field(default=None, description="Defaults to 14 days after start")
    status: Literal["scheduled", "completed", "missed", "cancelled"] | None = None


async def get_study_sessions(ctx: ToolContext, args: GetStudySessionsIn) -> Listing[StudySession]:
    start = args.start_date or ctx.today
    end = args.end_date or start + timedelta(days=14)
    return listing(await ctx.backend.list_study_sessions(start=start, end=end, status=args.status))


class CreateStudyPlanIn(ToolInput):
    subject: str = Field(min_length=1, max_length=200)
    topics: list[str] = Field(default_factory=list, max_length=30, description="Topics to cover, in order")
    start_date: dt.date | None = Field(default=None, description="First study day; defaults to tomorrow")
    days: int = Field(default=5, ge=1, le=60, description="Number of days to spread the plan over")
    minutes_per_day: int = Field(default=90, ge=15, le=600)
    session_minutes: int = Field(default=60, ge=15, le=240)
    title: str | None = Field(default=None, max_length=300)


async def create_study_plan(ctx: ToolContext, args: CreateStudyPlanIn) -> StudyPlan:
    # The backend lays sessions out inside the user's study window around existing events;
    # the agent then saves exactly that draft.
    draft = await ctx.backend.generate_study_plan(args.to_backend(exclude={"title"}))
    if not draft.sessions:
        raise ToolError("No free study time was found in that period. Try more days or a shorter session length.")
    body = draft.model_dump(mode="json", by_alias=True, exclude_none=True)
    if args.title:
        body["title"] = args.title
    return await ctx.backend.create_study_plan(body)


class UpdateStudyPlanIn(ToolInput):
    plan_id: str = ID
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    end_date: dt.date | None = None
    status: Literal["draft", "active", "completed", "archived"] | None = None


async def update_study_plan(ctx: ToolContext, args: UpdateStudyPlanIn) -> StudyPlan:
    return await ctx.backend.update_study_plan(args.plan_id, args.to_backend(exclude={"plan_id"}))


class CreateStudySessionIn(ToolInput):
    topic: str = Field(min_length=1, max_length=300)
    date: dt.date
    start_time: HHMM
    end_time: HHMM
    subject_name: str | None = Field(default=None, max_length=200)
    priority: Literal["low", "medium", "high"] = "medium"
    study_plan_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


async def create_study_session(ctx: ToolContext, args: CreateStudySessionIn) -> StudySession:
    return await ctx.backend.create_study_session(args.to_backend())


class SessionIdIn(ToolInput):
    session_id: str = ID


async def complete_study_session(ctx: ToolContext, args: SessionIdIn) -> StudySession:
    return await ctx.backend.update_study_session(args.session_id, {"status": "completed"})


TOOLS = [
    ToolDefinition("get_subjects", "List the user's subjects/courses.", ToolDomain.STUDY, ToolRisk.READ,
                   NoInput, Listing[Subject], get_subjects),
    ToolDefinition("create_subject", "Add a subject/course the student is taking.", ToolDomain.STUDY, ToolRisk.MUTATE,
                   CreateSubjectIn, Subject, create_subject, approval_reason="Adds a subject."),
    ToolDefinition("get_study_plan", "Get one study plan by ID, or list study plans with their sessions.",
                   ToolDomain.STUDY, ToolRisk.READ, GetStudyPlanIn, Listing[StudyPlan], get_study_plan),
    ToolDefinition("get_study_sessions", "List scheduled or past study sessions in a date range.",
                   ToolDomain.STUDY, ToolRisk.READ, GetStudySessionsIn, Listing[StudySession], get_study_sessions),
    ToolDefinition("create_study_plan", "Create and save a study plan. Sessions are placed automatically inside the user's study window, avoiding existing events. Check subjects, tasks and the schedule first.",
                   ToolDomain.STUDY, ToolRisk.MUTATE, CreateStudyPlanIn, StudyPlan, create_study_plan,
                   approval_reason="Creates a study plan and schedules its sessions."),
    ToolDefinition("update_study_plan", "Rename, extend or change the status of a study plan.",
                   ToolDomain.STUDY, ToolRisk.MUTATE, UpdateStudyPlanIn, StudyPlan, update_study_plan,
                   approval_reason="Changes a study plan."),
    ToolDefinition("create_study_session", "Schedule one study session.", ToolDomain.STUDY, ToolRisk.MUTATE,
                   CreateStudySessionIn, StudySession, create_study_session,
                   approval_reason="Schedules a study session."),
    ToolDefinition("complete_study_session", "Mark a study session as completed.", ToolDomain.STUDY, ToolRisk.MUTATE,
                   SessionIdIn, StudySession, complete_study_session,
                   approval_reason="Marks a study session as completed."),
]
