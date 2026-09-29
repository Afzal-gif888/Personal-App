"""Shared schema primitives. JSON bodies are camelCase on the wire; Python stays snake_case."""

from datetime import datetime, time
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from app.core.timeutils import as_utc

T = TypeVar("T")


class APIModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class InputModel(APIModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", str_strip_whitespace=True
    )


# Decimals go out as JSON numbers (pydantic's default is a string).
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
MoneyIn = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
# Wall-clock times go out as HH:MM, matching the frontend.
HHMM = Annotated[time, PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str, when_used="json")]
UTCDateTime = Annotated[datetime, AfterValidator(as_utc)]
Currency = Annotated[str, Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")]


class Page(APIModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class Message(APIModel):
    message: str
