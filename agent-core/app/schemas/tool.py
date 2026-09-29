"""Tool metadata and execution records."""

import datetime as dt
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

# Times go to the backend as HH:MM, its API convention.
HHMM = Annotated[dt.time, PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str, when_used="json")]


class ToolRisk(StrEnum):
    READ = "read"  # no side effects: always runs
    MUTATE = "mutate"  # creates/updates the user's own data: runs or queues, per MUTATION_POLICY
    CONSEQUENTIAL = "consequential"  # deletes or external side effects: always needs approval


class ToolDomain(StrEnum):
    TASKS = "tasks"
    EVENTS = "events"
    REMINDERS = "reminders"
    STUDY = "study"
    FINANCE = "finance"
    GOALS = "goals"
    DOCUMENTS = "documents"
    MEMORY = "memory"


class ToolCallStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVAL_REQUIRED = "approval_required"
    SKIPPED = "skipped"


class ToolInput(BaseModel):
    """Base for tool inputs. The LLM sees snake_case; the backend receives camelCase via aliases."""

    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, alias_generator=to_camel, populate_by_name=True
    )

    def to_backend(self, *, exclude: set[str] | None = None) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True, exclude=exclude)


class NoInput(ToolInput):
    pass


class ToolOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ToolCallRequest(BaseModel):
    """A tool call the LLM asked for."""

    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class ToolCallRecord(BaseModel):
    """What happened to one tool call. `input` is redacted before it is stored."""

    id: str
    name: str
    input: dict[str, Any]
    status: ToolCallStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    approval_id: str | None = None
    duration_ms: int = 0
