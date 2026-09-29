"""Reminder tools."""

import datetime as dt
from typing import Literal

from pydantic import Field

from app.backend.schemas import Reminder
from app.schemas.tool import HHMM, ToolDomain, ToolInput, ToolRisk
from app.tools.common import ID, Listing, listing
from app.tools.registry import ToolContext, ToolDefinition


class GetRemindersIn(ToolInput):
    status: Literal["pending", "snoozed", "completed", "cancelled", "active"] = Field(
        default="active", description="'active' means pending or snoozed"
    )


async def get_reminders(ctx: ToolContext, args: GetRemindersIn) -> Listing[Reminder]:
    status = ["pending", "snoozed"] if args.status == "active" else [args.status]
    return listing(await ctx.backend.list_reminders(status=status))


class CreateReminderIn(ToolInput):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    date: dt.date = Field(description="YYYY-MM-DD in the user's timezone (first occurrence for repeating reminders)")
    time: HHMM | None = Field(default=None, description="HH:MM, 24-hour; defaults to the user's preferred reminder time")
    repeat_rule: Literal["none", "daily", "weekly", "monthly", "yearly"] = "none"
    category: Literal["academic", "personal", "financial", "career", "general"] = "general"


async def create_reminder(ctx: ToolContext, args: CreateReminderIn) -> Reminder:
    body = args.to_backend()
    if args.time is None:
        body["time"] = ctx.user.preferences.get("default_reminder_time") or "09:00"
    return await ctx.backend.create_reminder(body)


class ReminderIdIn(ToolInput):
    reminder_id: str = ID


async def complete_reminder(ctx: ToolContext, args: ReminderIdIn) -> Reminder:
    return await ctx.backend.complete_reminder(args.reminder_id)


class SnoozeReminderIn(ToolInput):
    reminder_id: str = ID
    minutes: int = Field(default=30, ge=1, le=7 * 24 * 60)


async def snooze_reminder(ctx: ToolContext, args: SnoozeReminderIn) -> Reminder:
    return await ctx.backend.snooze_reminder(args.reminder_id, args.minutes)


async def cancel_reminder(ctx: ToolContext, args: ReminderIdIn) -> Reminder:
    return await ctx.backend.update_reminder(args.reminder_id, {"status": "cancelled"})


TOOLS = [
    ToolDefinition("get_reminders", "List the user's reminders.", ToolDomain.REMINDERS, ToolRisk.READ,
                   GetRemindersIn, Listing[Reminder], get_reminders),
    ToolDefinition("create_reminder", "Create a one-off or repeating reminder (e.g. every Monday: repeat_rule 'weekly' starting on the next Monday).",
                   ToolDomain.REMINDERS, ToolRisk.MUTATE, CreateReminderIn, Reminder, create_reminder,
                   approval_reason="Creates a reminder."),
    ToolDefinition("complete_reminder", "Mark a reminder done. Repeating reminders move to their next occurrence.",
                   ToolDomain.REMINDERS, ToolRisk.MUTATE, ReminderIdIn, Reminder, complete_reminder,
                   approval_reason="Marks a reminder as done."),
    ToolDefinition("snooze_reminder", "Snooze a reminder by a number of minutes.", ToolDomain.REMINDERS, ToolRisk.MUTATE,
                   SnoozeReminderIn, Reminder, snooze_reminder, approval_reason="Snoozes a reminder."),
    ToolDefinition("cancel_reminder", "Cancel a reminder so it no longer fires.", ToolDomain.REMINDERS, ToolRisk.MUTATE,
                   ReminderIdIn, Reminder, cancel_reminder, approval_reason="Cancels a reminder."),
]
