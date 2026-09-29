"""Task tools: academic, personal, financial, career and general to-dos."""

from datetime import date, timedelta
from typing import Literal

from pydantic import Field

from app.backend.schemas import Task
from app.schemas.tool import HHMM, ToolDomain, ToolInput, ToolRisk
from app.tools.common import ID, Deleted, Listing, listing
from app.tools.registry import ToolContext, ToolDefinition

Category = Literal["academic", "personal", "financial", "career", "general"]
Priority = Literal["low", "medium", "high"]
OPEN = ["pending", "in_progress"]


class GetTasksIn(ToolInput):
    status: Literal["open", "completed", "all"] = "open"
    category: Category | None = None
    priority: Priority | None = None
    due_within_days: int | None = Field(default=None, ge=0, le=365, description="Only tasks due in the next N days (overdue included)")
    query: str | None = Field(default=None, max_length=200, description="Text to search in task titles")
    limit: int = Field(default=25, ge=1, le=100)


async def get_tasks(ctx: ToolContext, args: GetTasksIn) -> Listing[Task]:
    status = {"open": OPEN, "completed": ["completed"], "all": None}[args.status]
    page = await ctx.backend.list_tasks(
        status=status, category=args.category, priority=args.priority, q=args.query or None,
        due_to=ctx.today + timedelta(days=args.due_within_days) if args.due_within_days is not None else None,
        page_size=args.limit,
    )
    return listing(page.items, page.total)


class GetTaskIn(ToolInput):
    task_id: str = ID


async def get_task(ctx: ToolContext, args: GetTaskIn) -> Task:
    return await ctx.backend.get_task(args.task_id)


class CreateTaskIn(ToolInput):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    category: Category = "general"
    priority: Priority = "medium"
    due_date: date | None = Field(default=None, description="YYYY-MM-DD in the user's timezone")
    due_time: HHMM | None = Field(default=None, description="HH:MM, 24-hour")
    subject: str | None = Field(default=None, max_length=200, description="Subject name for academic tasks")


async def create_task(ctx: ToolContext, args: CreateTaskIn) -> Task:
    return await ctx.backend.create_task(args.to_backend())


class UpdateTaskIn(ToolInput):
    task_id: str = ID
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    category: Category | None = None
    priority: Priority | None = None
    status: Literal["pending", "in_progress", "completed", "cancelled"] | None = None
    due_date: date | None = None
    due_time: HHMM | None = None


async def update_task(ctx: ToolContext, args: UpdateTaskIn) -> Task:
    return await ctx.backend.update_task(args.task_id, args.to_backend(exclude={"task_id"}))


class TaskIdIn(ToolInput):
    task_id: str = ID


async def complete_task(ctx: ToolContext, args: TaskIdIn) -> Task:
    return await ctx.backend.update_task(args.task_id, {"status": "completed"})


async def delete_task(ctx: ToolContext, args: TaskIdIn) -> Deleted:
    task = await ctx.backend.get_task(args.task_id)
    await ctx.backend.delete_task(args.task_id)
    return Deleted(id=args.task_id, summary=f"Deleted task '{task.title}'")


TOOLS = [
    ToolDefinition("get_tasks", "List the user's tasks with status, priority, category and due date. 'open' includes pending and in-progress; overdue tasks are included.",
                   ToolDomain.TASKS, ToolRisk.READ, GetTasksIn, Listing[Task], get_tasks),
    ToolDefinition("get_task", "Get one task by ID.", ToolDomain.TASKS, ToolRisk.READ, GetTaskIn, Task, get_task),
    ToolDefinition("create_task", "Create a task (academic, personal, financial, career or general).",
                   ToolDomain.TASKS, ToolRisk.MUTATE, CreateTaskIn, Task, create_task,
                   approval_reason="Creates a new task."),
    ToolDefinition("update_task", "Change a task's title, details, priority, status or due date. Use IDs from get_tasks.",
                   ToolDomain.TASKS, ToolRisk.MUTATE, UpdateTaskIn, Task, update_task,
                   approval_reason="Changes an existing task."),
    ToolDefinition("complete_task", "Mark a task as completed. Use the ID from get_tasks.",
                   ToolDomain.TASKS, ToolRisk.MUTATE, TaskIdIn, Task, complete_task,
                   approval_reason="Marks a task as completed."),
    ToolDefinition("delete_task", "Permanently delete a task. Always requires the user's approval.",
                   ToolDomain.TASKS, ToolRisk.CONSEQUENTIAL, TaskIdIn, Deleted, delete_task,
                   approval_reason="Permanently deletes a task. This can't be undone."),
]
