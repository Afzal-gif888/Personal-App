from datetime import timedelta

import pytest

from app.approvals.manager import (
    ApprovalExpiredError,
    ApprovalManager,
    ApprovalNotFoundError,
    ApprovalStateError,
    ApprovalStatus,
    InMemoryApprovalStore,
    utcnow,
)
from tests.fakes import USER_A, USER_B


@pytest.fixture
def manager(tool_ctx):
    h, ctx = tool_ctx
    return ApprovalManager(InMemoryApprovalStore(), ttl_seconds=3600, registry=h.services.registry), h, ctx


async def _request_delete(manager, h, ctx):
    task_id = h.fake.data[USER_A]["tasks"][0]["id"]
    tool = h.services.registry.get("delete_task")
    approval = await manager.request(user_id=USER_A, run_id="run_1", tool=tool, tool_call_id="toolu_1",
                                     payload=tool.parse({"task_id": task_id}).model_dump(mode="json"))
    return approval, task_id


async def test_approval_required_payload_shape(manager):
    mgr, h, ctx = manager
    approval, task_id = await _request_delete(mgr, h, ctx)
    req = approval.to_request()
    assert req.action_type == "delete_task" and req.action_payload == {"task_id": task_id}
    assert "can't be undone" in req.reason and req.expires_at > utcnow()
    assert task_id in [t["id"] for t in h.fake.data[USER_A]["tasks"]]  # nothing ran yet


async def test_approve_runs_exactly_the_stored_payload_once(manager):
    mgr, h, ctx = manager
    approval, task_id = await _request_delete(mgr, h, ctx)
    done = await mgr.approve(approval.id, ctx)
    assert done.status == ApprovalStatus.APPROVED and done.result["deleted"]
    assert task_id not in [t["id"] for t in h.fake.data[USER_A]["tasks"]]
    with pytest.raises(ApprovalStateError):
        await mgr.approve(approval.id, ctx)


async def test_reject_discards(manager):
    mgr, h, ctx = manager
    approval, task_id = await _request_delete(mgr, h, ctx)
    assert (await mgr.reject(approval.id, USER_A)).status == ApprovalStatus.REJECTED
    assert task_id in [t["id"] for t in h.fake.data[USER_A]["tasks"]]
    with pytest.raises(ApprovalStateError):
        await mgr.approve(approval.id, ctx)


async def test_expired_approvals_cannot_run(manager):
    mgr, h, ctx = manager
    approval, task_id = await _request_delete(mgr, h, ctx)
    stored = await mgr.store.get(approval.id)
    stored.expires_at = utcnow() - timedelta(seconds=1)
    await mgr.store.save(stored)
    with pytest.raises(ApprovalExpiredError):
        await mgr.approve(approval.id, ctx)
    assert (await mgr.get(approval.id, USER_A)).status == ApprovalStatus.EXPIRED
    assert task_id in [t["id"] for t in h.fake.data[USER_A]["tasks"]]


async def test_expire_stale_sweeps(manager):
    mgr, h, ctx = manager
    mgr.ttl = timedelta(seconds=-1)
    await _request_delete(mgr, h, ctx)
    assert await mgr.expire_stale() == 1


async def test_other_users_cannot_see_or_decide(manager):
    mgr, h, ctx = manager
    approval, _ = await _request_delete(mgr, h, ctx)
    with pytest.raises(ApprovalNotFoundError):
        await mgr.get(approval.id, USER_B)
    with pytest.raises(ApprovalNotFoundError):
        await mgr.reject(approval.id, USER_B)


async def test_failed_action_is_recorded(manager):
    mgr, h, ctx = manager
    approval, task_id = await _request_delete(mgr, h, ctx)
    h.fake.data[USER_A]["tasks"] = [t for t in h.fake.data[USER_A]["tasks"] if t["id"] != task_id]
    done = await mgr.approve(approval.id, ctx)
    assert done.status == ApprovalStatus.FAILED and "not found" in done.error
