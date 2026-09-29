"""Goal tools: academic, financial, career and personal goals."""

from datetime import date
from typing import Literal

from pydantic import Field

from app.backend.schemas import Goal
from app.schemas.tool import ToolDomain, ToolInput, ToolRisk
from app.tools.common import ID, Listing, listing
from app.tools.registry import ToolContext, ToolDefinition, ToolInputError

Category = Literal["academic", "financial", "career", "personal", "general"]
Status = Literal["active", "on_hold", "completed", "abandoned"]


class GetGoalsIn(ToolInput):
    status: Status | None = "active"
    category: Category | None = None


async def get_goals(ctx: ToolContext, args: GetGoalsIn) -> Listing[Goal]:
    return listing(await ctx.backend.list_goals(status=args.status, category=args.category))


class CreateGoalIn(ToolInput):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    category: Category = "general"
    target_value: float | None = Field(default=None, ge=0, description="Numeric target, e.g. 20000 for 'save ₹20,000'")
    current_value: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40, description="e.g. 'INR', 'hours', 'applications'")
    deadline: date | None = None


async def create_goal(ctx: ToolContext, args: CreateGoalIn) -> Goal:
    return await ctx.backend.create_goal(args.to_backend())


class UpdateGoalIn(ToolInput):
    goal_id: str = ID
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    target_value: float | None = Field(default=None, ge=0)
    current_value: float | None = Field(default=None, ge=0)
    deadline: date | None = None
    status: Status | None = None


async def update_goal(ctx: ToolContext, args: UpdateGoalIn) -> Goal:
    return await ctx.backend.update_goal(args.goal_id, args.to_backend(exclude={"goal_id"}))


class GoalProgressIn(ToolInput):
    goal_id: str = ID
    progress: int | None = Field(default=None, ge=0, le=100, description="Percent complete")
    current_value: float | None = Field(default=None, ge=0, description="New current value for numeric goals")


async def update_goal_progress(ctx: ToolContext, args: GoalProgressIn) -> Goal:
    patch: dict = {}
    if args.progress is not None:
        patch["manualProgress"] = args.progress
    if args.current_value is not None:
        patch["currentValue"] = args.current_value
    if not patch:
        raise ToolInputError("Provide progress or current_value")
    if args.progress == 100:
        patch["status"] = "completed"
    return await ctx.backend.update_goal(args.goal_id, patch)


TOOLS = [
    ToolDefinition("get_goals", "List goals with progress and deadlines.", ToolDomain.GOALS, ToolRisk.READ,
                   GetGoalsIn, Listing[Goal], get_goals),
    ToolDefinition("create_goal", "Create a goal (e.g. save money, land an internship, study hours).",
                   ToolDomain.GOALS, ToolRisk.MUTATE, CreateGoalIn, Goal, create_goal, approval_reason="Creates a goal."),
    ToolDefinition("update_goal", "Edit a goal's details or status.", ToolDomain.GOALS, ToolRisk.MUTATE,
                   UpdateGoalIn, Goal, update_goal, approval_reason="Changes a goal."),
    ToolDefinition("update_goal_progress", "Set a goal's progress percent or current value. 100% completes it.",
                   ToolDomain.GOALS, ToolRisk.MUTATE, GoalProgressIn, Goal, update_goal_progress,
                   approval_reason="Updates a goal's progress."),
]
