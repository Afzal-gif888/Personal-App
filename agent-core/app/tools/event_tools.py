"""Calendar tools: classes, meetings, appointments, interviews, exams and personal events."""

import datetime as dt
from datetime import time, timedelta
from typing import Literal

from pydantic import Field, model_validator

from app.backend.schemas import Event
from app.schemas.tool import HHMM, ToolDomain, ToolInput, ToolRisk
from app.tools.common import ID, Deleted, Listing, listing
from app.tools.registry import ToolContext, ToolDefinition

EventType = Literal[
    "class", "meeting", "project_meeting", "team_meeting", "interview", "appointment",
    "exam", "deadline", "personal", "general", "other",
]
MAX_RANGE_DAYS = 62


class GetEventsIn(ToolInput):
    start_date: dt.date | None = Field(default=None, description="Defaults to today")
    end_date: dt.date | None = Field(default=None, description="Inclusive; defaults to 7 days after start")
    event_type: EventType | None = None

    @model_validator(mode="after")
    def _range(self):
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be on or after start_date")
            if (self.end_date - self.start_date).days > MAX_RANGE_DAYS:
                raise ValueError(f"date range cannot exceed {MAX_RANGE_DAYS} days")
        return self


async def get_events(ctx: ToolContext, args: GetEventsIn) -> Listing[Event]:
    start = args.start_date or ctx.today
    end = args.end_date or start + timedelta(days=7)
    return listing(await ctx.backend.list_events(start=start, end=end, event_type=args.event_type))


class CreateEventIn(ToolInput):
    title: str = Field(min_length=1, max_length=300)
    event_type: EventType = "general"
    date: dt.date = Field(description="YYYY-MM-DD in the user's timezone")
    start_time: HHMM = Field(description="HH:MM, 24-hour, user's timezone")
    end_time: HHMM | None = Field(default=None, description="HH:MM; defaults to one hour after start")
    location: str | None = Field(default=None, max_length=300)
    meeting_url: str | None = Field(default=None, max_length=1024)
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _times(self):
        if self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


async def create_event(ctx: ToolContext, args: CreateEventIn) -> Event:
    body = args.to_backend()
    if args.end_time is None:
        end = (args.start_time.hour + 1) % 24
        body["endTime"] = time(end, args.start_time.minute).strftime("%H:%M") if end else "23:59"
    return await ctx.backend.create_event(body)


class UpdateEventIn(ToolInput):
    event_id: str = ID
    title: str | None = Field(default=None, min_length=1, max_length=300)
    event_type: EventType | None = None
    date: dt.date | None = None
    start_time: HHMM | None = None
    end_time: HHMM | None = None
    location: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2000)


async def update_event(ctx: ToolContext, args: UpdateEventIn) -> Event:
    return await ctx.backend.update_event(args.event_id, args.to_backend(exclude={"event_id"}))


class EventIdIn(ToolInput):
    event_id: str = ID


async def delete_event(ctx: ToolContext, args: EventIdIn) -> Deleted:
    await ctx.backend.delete_event(args.event_id)
    return Deleted(id=args.event_id, summary="Deleted the event")


TOOLS = [
    ToolDefinition("get_events", "List calendar events (classes, meetings, interviews, exams, appointments) in a date range of up to 62 days.",
                   ToolDomain.EVENTS, ToolRisk.READ, GetEventsIn, Listing[Event], get_events),
    ToolDefinition("create_event", "Add an event or meeting to the calendar. Dates and times are in the user's timezone.",
                   ToolDomain.EVENTS, ToolRisk.MUTATE, CreateEventIn, Event, create_event,
                   approval_reason="Adds an event to your calendar."),
    ToolDefinition("update_event", "Reschedule or edit an existing event. Use the ID from get_events.",
                   ToolDomain.EVENTS, ToolRisk.MUTATE, UpdateEventIn, Event, update_event,
                   approval_reason="Changes a calendar event."),
    ToolDefinition("delete_event", "Delete a calendar event. Always requires the user's approval.",
                   ToolDomain.EVENTS, ToolRisk.CONSEQUENTIAL, EventIdIn, Deleted, delete_event,
                   approval_reason="Removes an event from your calendar. This can't be undone."),
]
