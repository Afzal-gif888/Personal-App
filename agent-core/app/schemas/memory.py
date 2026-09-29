"""Memory records."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MemoryKey(StrEnum):
    """The only facts long-term memory may hold. Anything else is not remembered."""

    PREFERRED_STUDY_START = "preferred_study_start"
    PREFERRED_STUDY_END = "preferred_study_end"
    DEFAULT_REMINDER_TIME = "default_reminder_time"
    DAILY_STUDY_GOAL_MINUTES = "daily_study_goal_minutes"
    TIMEZONE = "timezone"


class MemoryFact(BaseModel):
    key: MemoryKey
    value: Any
    source: str = "user_statement"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConversationTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str
