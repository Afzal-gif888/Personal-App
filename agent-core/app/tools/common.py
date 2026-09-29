"""Output shapes shared by the domain tool modules."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.schemas.tool import ToolOutput

T = TypeVar("T", bound=BaseModel)

ID = Field(min_length=1, max_length=64, description="ID of an existing item, taken from an earlier tool result")


class Listing(ToolOutput, Generic[T]):
    items: list[T]
    total: int


class Deleted(ToolOutput):
    id: str
    deleted: bool = True
    summary: str


def listing(items: list[T], total: int | None = None) -> Listing[T]:
    return Listing[T](items=items, total=len(items) if total is None else total)
