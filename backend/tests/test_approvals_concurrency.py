"""Tests for atomic and idempotent approval execution under concurrency."""

import time
from concurrent.futures import ThreadPoolExecutor

from app.models import Approval, User
from app.models.enums import ApprovalStatus


def test_concurrent_approvals_execute_exactly_once(client, auth, db, monkeypatch):
    """Two concurrent approvals on the same pending item must result in exactly 1 execution."""
    execution_count = 0

    def mock_execute_action(approval, token):
        nonlocal execution_count
        execution_count += 1
        time.sleep(0.15)  # Simulate network latency to ensure threads overlap
        return {"summary": "Task created", "task_id": "tsk_123"}

    monkeypatch.setattr("app.agent.remote.execute_action", mock_execute_action)

    user = db.query(User).filter_by(email="student@example.com").first()
    assert user is not None
    approval = Approval(
        user_id=user.id,
        action="create_task",
        action_label="Create task",
        title="Test Task Approval",
        description="A task waiting for approval",
        payload={"source": "agent_core", "args": {"title": "Finish report"}},
        status=ApprovalStatus.PENDING,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    approval_id = str(approval.id)

    statuses = []
    responses = []

    def call_approve():
        res = client.post(f"/api/v1/approvals/{approval_id}/approve", headers=auth)
        statuses.append(res.status_code)
        responses.append(res.json())

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(call_approve)
        f2 = executor.submit(call_approve)
        f1.result()
        f2.result()

    # Exactly one request must succeed with 200 and one must fail with 409 Conflict
    assert 200 in statuses, f"Expected HTTP 200 in {statuses}, responses: {responses}"
    assert 409 in statuses, f"Expected HTTP 409 in {statuses}, responses: {responses}"

    # Action executed exactly once
    assert execution_count == 1

    # Database state must be APPROVED
    db.expire_all()
    final_appr = db.get(Approval, approval.id)
    assert final_appr.status == ApprovalStatus.APPROVED
    assert final_appr.result == {"summary": "Task created", "task_id": "tsk_123"}
