"""AGENT_CORE_MODE=agent: the Agent Core's LangGraph agent reasons and acts; the backend persists the
run, tool calls and approvals, and executes approved Agent Core actions through the Agent Core."""

import httpx
import pytest
from sqlalchemy import select

from app.agent import remote
from app.core.config import get_settings
from app.models import AgentRun, Approval, ToolCall
from app.models.enums import AgentRunStatus, ApprovalStatus, ToolCallStatus


class FakeAgentCore:
    """Stands in for the Agent Core's HTTP API and records what the backend sent."""

    def __init__(self, run_response: dict, execute_response: tuple[int, dict] | None = None) -> None:
        self.run_response = run_response
        self.execute_response = execute_response or (200, {"status": "completed", "result": {"id": "t-1", "title": "Done"},
                                                            "summary": "Deleted task 'Essay'"})
        self.calls: list[tuple[str, dict, str]] = []

    def __call__(self, path: str, body: dict, user_token: str) -> httpx.Response:
        self.calls.append((path, body, user_token))
        if path == "/agent/run":
            return httpx.Response(200, json=self.run_response)
        status, payload = self.execute_response
        return httpx.Response(status, json=payload)


RUN_WITH_APPROVAL = {
    "run_id": "run_abc",
    "status": "approval_required",
    "response": "Deleting 'Essay' needs your approval.",
    "tool_calls": [
        {"id": "t1", "name": "get_tasks", "input": {"query": "essay"}, "status": "completed",
         "output": {"items": [{"id": "task-9", "title": "Essay"}], "total": 1}, "duration_ms": 12},
        {"id": "t2", "name": "delete_task", "input": {"task_id": "task-9"}, "status": "approval_required",
         "approval_id": "apr_1", "duration_ms": 3},
    ],
    "approvals": [{"approval_id": "apr_1", "action_type": "delete_task", "action_payload": {"task_id": "task-9"},
                   "reason": "Permanently deletes a task.", "expires_at": "2099-01-01T00:00:00+00:00"}],
    "events": [{"type": "RUN_STARTED"}, {"type": "TOOL_COMPLETED"}, {"type": "APPROVAL_REQUIRED"}, {"type": "RUN_COMPLETED"}],
    "metadata": {"model": "gemini-3.8-flash", "iterations": 3},
}


@pytest.fixture
def agent_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "agent_core_mode", "agent")


def _send(client, auth, text="Delete my essay task"):
    conv = client.post("/api/v1/conversations", headers=auth, json={}).json()
    resp = client.post(f"/api/v1/conversations/{conv['id']}/messages", headers=auth, json={"content": text})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_chat_runs_the_agent_core_and_persists_everything(client, auth, db, agent_mode, monkeypatch):
    fake = FakeAgentCore(RUN_WITH_APPROVAL)
    monkeypatch.setattr(remote, "_post", fake)
    body = _send(client, auth)

    path, sent, token = fake.calls[0]
    assert path == "/agent/run" and sent["message"] == "Delete my essay task"
    assert token == auth["Authorization"].removeprefix("Bearer ")  # the user's own token is forwarded

    run = db.scalar(select(AgentRun))
    assert run.status == AgentRunStatus.WAITING_FOR_APPROVAL
    assert run.meta["engine"] == "langgraph" and run.meta["agent_core_run_id"] == "run_abc"
    calls = list(db.scalars(select(ToolCall).order_by(ToolCall.created_at)))
    assert [(c.tool_name, c.status) for c in calls] == [
        ("get_tasks", ToolCallStatus.COMPLETED), ("delete_task", ToolCallStatus.WAITING_FOR_APPROVAL)]
    approval = db.scalar(select(Approval))
    assert approval.status == ApprovalStatus.PENDING and approval.action == "delete_task"
    assert approval.payload["source"] == "agent_core" and approval.payload["args"] == {"task_id": "task-9"}
    assert approval.tool_call_id == calls[1].id

    msg = body["assistantMessage"]
    assert msg["content"] == "Deleting 'Essay' needs your approval."
    assert [s["toolName"] for s in msg["metadata"]["steps"]] == ["get_tasks", "delete_task"]
    assert msg["metadata"]["actions"][0]["approvalId"] == str(approval.id)


def test_approving_executes_through_the_agent_core(client, auth, db, agent_mode, monkeypatch):
    fake = FakeAgentCore(RUN_WITH_APPROVAL)
    monkeypatch.setattr(remote, "_post", fake)
    _send(client, auth)
    approval_id = db.scalar(select(Approval)).id

    resp = client.post(f"/api/v1/approvals/{approval_id}/approve", headers=auth)
    assert resp.status_code == 200 and resp.json()["status"] == "approved"
    path, sent, _ = fake.calls[-1]
    assert path == "/agent/actions/execute"
    assert sent == {"action_type": "delete_task", "action_payload": {"task_id": "task-9"}}  # exactly the stored payload
    db.expire_all()
    assert db.scalar(select(AgentRun)).status == AgentRunStatus.COMPLETED
    assert db.scalar(select(ToolCall).where(ToolCall.tool_name == "delete_task")).status == ToolCallStatus.COMPLETED
    # A second decision is refused, and the Agent Core is not called again.
    assert client.post(f"/api/v1/approvals/{approval_id}/approve", headers=auth).status_code == 409
    assert sum(1 for c in fake.calls if c[0] == "/agent/actions/execute") == 1


def test_failed_execution_keeps_the_approval_pending(client, auth, db, agent_mode, monkeypatch):
    fake = FakeAgentCore(RUN_WITH_APPROVAL, execute_response=(409, {"error": {"code": "INVALID_STATE", "message": "That item was not found."}}))
    monkeypatch.setattr(remote, "_post", fake)
    _send(client, auth)
    approval_id = db.scalar(select(Approval)).id
    resp = client.post(f"/api/v1/approvals/{approval_id}/approve", headers=auth)
    assert resp.status_code == 422 and "not found" in resp.json()["error"]["message"]
    db.expire_all()
    assert db.get(Approval, approval_id).status == ApprovalStatus.PENDING
    assert client.post(f"/api/v1/approvals/{approval_id}/reject", headers=auth).json()["status"] == "rejected"


def test_other_users_cannot_approve_agent_core_actions(client, auth, other_auth, db, agent_mode, monkeypatch):
    fake = FakeAgentCore(RUN_WITH_APPROVAL)
    monkeypatch.setattr(remote, "_post", fake)
    _send(client, auth)
    approval_id = db.scalar(select(Approval)).id
    assert client.post(f"/api/v1/approvals/{approval_id}/approve", headers=other_auth).status_code == 404
    assert not any(c[0] == "/agent/actions/execute" for c in fake.calls)


def test_agent_core_failures_are_recorded(client, auth, db, agent_mode, monkeypatch):
    failed = {"run_id": "run_x", "status": "failed", "response": "The assistant is busy right now.", "tool_calls": [],
              "approvals": [], "events": [{"type": "RUN_FAILED"}], "error": {"code": "LLM_ERROR", "message": "The assistant is busy right now."},
              "metadata": {}}
    monkeypatch.setattr(remote, "_post", FakeAgentCore(failed))
    body = _send(client, auth, "hello")
    run = db.scalar(select(AgentRun))
    assert run.status == AgentRunStatus.FAILED and run.error_message == "The assistant is busy right now."
    assert body["assistantMessage"]["metadata"]["status"] == "error"


def test_unreachable_agent_core(client, auth, db, agent_mode, monkeypatch):
    def down(*_args):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(remote, "_post", down)
    body = _send(client, auth, "hello")
    assert body["assistantMessage"]["content"] == "Couldn't reach the assistant service. Please try again."
    assert db.scalar(select(AgentRun)).status == AgentRunStatus.FAILED
