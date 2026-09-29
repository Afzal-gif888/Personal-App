"""Request budget: cap how many model calls the Agent Core makes, per minute and per day.

Free tiers are small (OpenRouter free models: 20/minute, 50/day). Once a cap is reached the
assistant answers "try again later" without calling the provider, so no request is spent on a
call that would only be rate-limited. Counts are per process and reset at midnight UTC.
"""

import time
from collections import deque
from datetime import UTC, datetime
from typing import Any

from app.llm.base import LLMError, LLMProvider, LLMResult, LLMToolSpec, Purpose


class RequestBudget:
    def __init__(self, per_minute: int = 0, per_day: int = 0) -> None:
        self.per_minute = per_minute
        self.per_day = per_day
        self._recent: deque[float] = deque()
        self._day = ""
        self._today = 0

    def take(self) -> None:
        """Reserve one request, or raise LLMError if a cap is reached."""
        now = time.monotonic()
        day = datetime.now(UTC).date().isoformat()
        if day != self._day:
            self._day, self._today = day, 0
        while self._recent and now - self._recent[0] >= 60:
            self._recent.popleft()
        if self.per_day and self._today >= self.per_day:
            raise LLMError("The assistant has used today's request allowance. It resets at midnight UTC.",
                           rate_limited=True)
        if self.per_minute and len(self._recent) >= self.per_minute:
            raise LLMError("The assistant is handling a lot right now. Please try again in a minute.",
                           retryable=True, rate_limited=True)
        self._recent.append(now)
        self._today += 1

    @property
    def used_today(self) -> int:
        return self._today


class BudgetedProvider(LLMProvider):
    """Wraps a provider so every model call first takes from the request budget."""

    def __init__(self, inner: LLMProvider, budget: RequestBudget) -> None:
        self.inner = inner
        self.budget = budget
        self.name = inner.name
        self.model = inner.model

    async def invoke(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[LLMToolSpec], purpose: Purpose = "act"
    ) -> LLMResult:
        self.budget.take()
        return await self.inner.invoke(system=system, messages=messages, tools=tools, purpose=purpose)

    async def aclose(self) -> None:
        await self.inner.aclose()
