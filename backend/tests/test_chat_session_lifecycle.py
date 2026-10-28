"""Test that the database session is not held during long Agent Core HTTP calls."""

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.agent import remote
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import AgentRun, Conversation, Message, ToolCall
from app.models.enums import AgentRunStatus, MessageRole, ToolCallStatus


@pytest.fixture
def agent_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "agent_core_mode", "agent")


def test_session_is_released_during_agent_call(client, auth, db, agent_mode, monkeypatch):
    """Verify that during the Agent Core HTTP call, the DB session is closed and released,
    and a separate session can observe that the initial AgentRun is already committed as RUNNING."""
    observed_state = {}

    def fake_post(path: str, body: dict, user_token: str) -> httpx.Response:
        if path == "/agent/run":
            # Check from an independent session that the run and user message were committed
            with SessionLocal() as inspection_db:
                running_runs = list(inspection_db.scalars(
                    select(AgentRun).where(AgentRun.status == AgentRunStatus.RUNNING)
                ))
                user_msgs = list(inspection_db.scalars(
                    select(Message).where(Message.role == MessageRole.USER)
                ))
                observed_state["running_runs_count"] = len(running_runs)
                observed_state["user_msgs_count"] = len(user_msgs)
                if running_runs:
                    observed_state["run_id"] = running_runs[0].id

            return httpx.Response(200, json={
                "run_id": "run_test_lifecycle",
                "status": "completed",
                "response": "Here is the answer.",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "name": "get_tasks",
                        "input": {},
                        "status": "completed",
                        "output": {"items": []},
                        "duration_ms": 15,
                    }
                ],
                "approvals": [],
                "events": [{"type": "RUN_STARTED"}, {"type": "RUN_COMPLETED"}],
                "metadata": {"model": "test-model", "iterations": 1},
            })
        return httpx.Response(200, json={})

    monkeypatch.setattr(remote, "_post", fake_post)

    conv_resp = client.post("/api/v1/conversations", headers=auth, json={}).json()
    msg_resp = client.post(
        f"/api/v1/conversations/{conv_resp['id']}/messages",
        headers=auth,
        json={"content": "Check my tasks please"},
    )
    assert msg_resp.status_code == 201

    # Assert that during the call, initial state was committed and observable
    assert observed_state["running_runs_count"] == 1
    assert observed_state["user_msgs_count"] >= 1

    # Assert that after call completed, session was reopened and completed state was persisted
    db.expire_all()
    run = db.get(AgentRun, observed_state["run_id"])
    assert run is not None
    assert run.status == AgentRunStatus.COMPLETED
    assert run.meta["agent_core_run_id"] == "run_test_lifecycle"

    # User message and assistant message are both persisted and linked
    conv_id = uuid.UUID(conv_resp["id"])
    user_msg = db.scalar(
        select(Message).where(Message.conversation_id == conv_id, Message.role == MessageRole.USER)
    )
    asst_msg = db.scalar(
        select(Message).where(Message.conversation_id == conv_id, Message.role == MessageRole.ASSISTANT)
    )
    assert user_msg.agent_run_id == run.id
    assert asst_msg.agent_run_id == run.id
    assert asst_msg.content == "Here is the answer."


def test_failed_call_reopens_session_and_records_failure(client, auth, db, agent_mode, monkeypatch):
    """Verify that when Agent Core HTTP call fails, session is reopened and error is persisted."""
    def down(*_args, **_kwargs):
        raise httpx.ConnectError("Service unreachable")

    monkeypatch.setattr(remote, "_post", down)

    conv_resp = client.post("/api/v1/conversations", headers=auth, json={}).json()
    msg_resp = client.post(
        f"/api/v1/conversations/{conv_resp['id']}/messages",
        headers=auth,
        json={"content": "Hello there"},
    )
    assert msg_resp.status_code == 201

    db.expire_all()
    run = db.scalar(select(AgentRun))
    assert run.status == AgentRunStatus.FAILED
    assert "Couldn't reach" in run.error_message
