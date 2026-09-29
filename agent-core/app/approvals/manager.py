"""Approval gate for consequential (and, by policy, mutating) actions.

When the agent wants to run a tool that needs approval, nothing executes. The validated input is
stored as a pending approval and the run returns APPROVAL_REQUIRED with `action_type`,
`action_payload` and `reason`. Approving later runs exactly that payload - never a re-generated
one - on behalf of the same user who owns the approval.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.agent import ApprovalRequest
from app.tools.registry import ToolContext, ToolDefinition, ToolError, ToolRegistry


def utcnow() -> datetime:
    return datetime.now(UTC)


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"  # approved, but the action itself failed


class PendingApproval(BaseModel):
    id: str
    user_id: str
    run_id: str
    tool_name: str
    tool_call_id: str
    payload: dict[str, Any]
    reason: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    decided_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_request(self) -> ApprovalRequest:
        return ApprovalRequest(
            approval_id=self.id, action_type=self.tool_name, action_payload=self.payload,
            reason=self.reason, expires_at=self.expires_at,
        )


class ApprovalError(Exception):
    pass


class ApprovalNotFoundError(ApprovalError):
    pass


class ApprovalExpiredError(ApprovalError):
    pass


class ApprovalStateError(ApprovalError):
    pass


class ApprovalStore(ABC):
    @abstractmethod
    async def save(self, approval: PendingApproval) -> None: ...

    @abstractmethod
    async def get(self, approval_id: str) -> PendingApproval | None: ...

    @abstractmethod
    async def list_pending(self) -> list[PendingApproval]: ...


class InMemoryApprovalStore(ApprovalStore):
    """Process-local store. Multi-instance deployments should persist approvals in the backend."""

    def __init__(self) -> None:
        self._items: dict[str, PendingApproval] = {}

    async def save(self, approval: PendingApproval) -> None:
        self._items[approval.id] = approval.model_copy(deep=True)

    async def get(self, approval_id: str) -> PendingApproval | None:
        item = self._items.get(approval_id)
        return item.model_copy(deep=True) if item else None

    async def list_pending(self) -> list[PendingApproval]:
        return [a.model_copy(deep=True) for a in self._items.values() if a.status == ApprovalStatus.PENDING]


class ApprovalManager:
    def __init__(self, store: ApprovalStore, *, ttl_seconds: int, registry: ToolRegistry) -> None:
        self.store = store
        self.ttl = timedelta(seconds=ttl_seconds)
        self.registry = registry
        self._lock = asyncio.Lock()  # one decision at a time, so an approval can't run twice

    async def request(self, *, user_id: str, run_id: str, tool: ToolDefinition, tool_call_id: str, payload: dict[str, Any]) -> PendingApproval:
        approval = PendingApproval(
            id=f"apr_{uuid.uuid4().hex}", user_id=user_id, run_id=run_id, tool_name=tool.name,
            tool_call_id=tool_call_id, payload=payload, reason=tool.approval_reason, expires_at=utcnow() + self.ttl,
        )
        await self.store.save(approval)
        return approval

    async def get(self, approval_id: str, user_id: str) -> PendingApproval:
        approval = await self.store.get(approval_id)
        # A different user's approval looks exactly like a missing one.
        if approval is None or approval.user_id != user_id:
            raise ApprovalNotFoundError("Approval not found")
        if approval.status == ApprovalStatus.PENDING and approval.expires_at <= utcnow():
            approval.status, approval.decided_at = ApprovalStatus.EXPIRED, utcnow()
            await self.store.save(approval)
        return approval

    async def approve(self, approval_id: str, ctx: ToolContext) -> PendingApproval:
        async with self._lock:
            approval = await self._pending(approval_id, ctx.user.user_id)
            tool = self.registry.get(approval.tool_name)
            if tool is None:
                raise ApprovalStateError("This action is no longer available")
            approval.decided_at = utcnow()
            try:
                approval.result = await self.registry.execute(tool, tool.parse(approval.payload), ctx)
                approval.status = ApprovalStatus.APPROVED
            except ToolError as exc:
                approval.status, approval.error = ApprovalStatus.FAILED, str(exc)
            await self.store.save(approval)
            return approval

    async def reject(self, approval_id: str, user_id: str) -> PendingApproval:
        async with self._lock:
            approval = await self._pending(approval_id, user_id)
            approval.status, approval.decided_at = ApprovalStatus.REJECTED, utcnow()
            await self.store.save(approval)
            return approval

    async def expire_stale(self) -> int:
        count = 0
        for approval in await self.store.list_pending():
            if approval.expires_at <= utcnow():
                approval.status, approval.decided_at = ApprovalStatus.EXPIRED, utcnow()
                await self.store.save(approval)
                count += 1
        return count

    async def _pending(self, approval_id: str, user_id: str) -> PendingApproval:
        approval = await self.get(approval_id, user_id)
        if approval.status == ApprovalStatus.EXPIRED:
            raise ApprovalExpiredError("This approval has expired. Ask the assistant again.")
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalStateError(f"This approval was already {approval.status.value}")
        return approval
