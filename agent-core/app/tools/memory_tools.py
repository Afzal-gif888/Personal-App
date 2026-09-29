"""The controlled path into long-term memory."""

from pydantic import Field

from app.memory.long_term import MemoryValidationError
from app.schemas.memory import MemoryKey
from app.schemas.tool import ToolDomain, ToolInput, ToolOutput, ToolRisk
from app.tools.registry import ToolContext, ToolDefinition, ToolError, ToolInputError


class RememberPreferenceIn(ToolInput):
    key: MemoryKey
    value: str | int = Field(description="HH:MM for times, minutes for the daily goal, an IANA name for timezone")


class Remembered(ToolOutput):
    key: str
    value: str | int
    summary: str


async def remember_preference(ctx: ToolContext, args: RememberPreferenceIn) -> Remembered:
    if ctx.memory is None:
        raise ToolError("Memory is not available.")
    try:
        fact = await ctx.memory.remember(ctx.backend, args.key, args.value)
    except MemoryValidationError as exc:
        raise ToolInputError(str(exc))
    return Remembered(key=fact.key.value, value=fact.value, summary=f"Saved {fact.key.value.replace('_', ' ')} = {fact.value}")


TOOLS = [
    ToolDefinition(
        "remember_preference",
        "Save a stable preference the user explicitly stated (preferred study start/end time, default reminder time, "
        "daily study goal, timezone). Only call when the user clearly asks for or states it - never guess.",
        ToolDomain.MEMORY, ToolRisk.MUTATE, RememberPreferenceIn, Remembered, remember_preference,
        approval_reason="Updates your saved preferences.",
    ),
]
