"""The HTTP service: health, auth, /agent/run, approvals and the backend-compat endpoint."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import SERVICE_TOKEN, make_settings
from tests.fakes import TOKEN_A, TOKEN_B, USER_A
from tests.mock_llm import MockLLMProvider

AUTH = {"Authorization": f"Bearer {SERVICE_TOKEN}", "X-User-Authorization": f"Bearer {TOKEN_A}"}


@pytest.fixture
def client(backend):
    app = create_app(make_settings(agent_core_service_token=SERVICE_TOKEN, llm_api_key="sk-ant-never-log-me-123456"), llm=MockLLMProvider(),
                     backend_transport=backend.transport())
    with TestClient(app) as c:
        yield c


def test_health_and_ready(client, backend):
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/ready")
    assert ready.status_code == 200 and ready.json()["checks"]["backend"] == "ok"
    assert ready.json()["checks"]["llm"] == "mock" and ready.json()["checks"]["tools"] >= 40
    backend.healthy = False
    assert client.get("/ready").status_code == 503


def test_service_token_is_required(client):
    body = {"message": "hi"}
    assert client.post("/agent/run", json=body, headers={"X-User-Authorization": f"Bearer {TOKEN_A}"}).status_code == 401
    bad = client.post("/agent/run", json=body, headers={**AUTH, "Authorization": "Bearer wrong"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "UNAUTHORIZED"
    assert client.post("/agent/run", json=body, headers={"Authorization": f"Bearer {SERVICE_TOKEN}"}).status_code == 401


def test_invalid_user_token_is_401(client):
    r = client.post("/agent/run", json={"message": "hi"}, headers={**AUTH, "X-User-Authorization": "Bearer nope"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"


def test_validation_errors_are_structured(client):
    r = client.post("/agent/run", json={"message": ""}, headers=AUTH)
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_REQUEST"
    assert r.json()["error"]["details"][0]["field"] == "message"


def test_run_returns_safe_structured_response(client):
    r = client.post("/agent/run", json={"message": "What bills are due this week?", "conversation_id": "c1"}, headers=AUTH)
    assert r.status_code == 200 and r.headers["x-request-id"]
    body = r.json()
    assert body["run_id"].startswith("run_") and body["status"] == "completed"
    assert body["tool_calls"][0]["name"] == "get_bills" and body["approval_required"] is False
    assert {"RUN_STARTED", "TOOL_COMPLETED", "RUN_COMPLETED"} <= {e["type"] for e in body["events"]}
    # No prompts or transcripts leak out: only the reply and safe metadata.
    text = r.text
    assert "You are the It's Personal assistant" not in text and "tool_result" not in text


def test_user_id_spoofing_is_forbidden(client):
    r = client.post("/agent/run", json={"message": "tasks?", "user_id": "someone-else"}, headers=AUTH)
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"


def test_scopes_header_restricts_tools(client, backend):
    r = client.post("/agent/run", json={"message": "Remind me to pay rent tomorrow at 9 AM"},
                    headers={**AUTH, "X-Agent-Scopes": "reminders:read"})
    call = r.json()["tool_calls"][0]
    assert call["status"] == "failed" and "allowed" in call["error"]
    assert len(backend.data[USER_A]["reminders"]) == 1


def test_approval_flow_over_http(client, backend):
    r = client.post("/agent/run", json={"message": "Delete my DBMS assignment task"}, headers=AUTH).json()
    assert r["status"] == "approval_required"
    approval_id = r["approvals"][0]["approval_id"]
    other = {**AUTH, "X-User-Authorization": f"Bearer {TOKEN_B}"}
    assert client.post(f"/agent/approvals/{approval_id}/approve", headers=other).status_code == 404
    assert client.get(f"/agent/approvals/{approval_id}", headers=AUTH).json()["status"] == "pending"
    done = client.post(f"/agent/approvals/{approval_id}/approve", headers=AUTH)
    assert done.status_code == 200 and done.json()["status"] == "approved"
    assert "DBMS assignment" not in [t["title"] for t in backend.data[USER_A]["tasks"]]
    again = client.post(f"/agent/approvals/{approval_id}/approve", headers=AUTH)
    assert again.status_code == 409 and again.json()["error"]["code"] == "INVALID_STATE"


def test_reject_over_http(client, backend):
    r = client.post("/agent/run", json={"message": "Delete my DBMS assignment task"}, headers=AUTH).json()
    approval_id = r["approvals"][0]["approval_id"]
    assert client.post(f"/agent/approvals/{approval_id}/reject", headers=AUTH).json()["status"] == "rejected"
    assert "DBMS assignment" in [t["title"] for t in backend.data[USER_A]["tasks"]]
    assert client.post("/agent/approvals/apr_missing/approve", headers=AUTH).status_code == 404


def test_tool_catalogue(client):
    tools = {t["name"]: t for t in client.get("/agent/tools", headers=AUTH).json()}
    assert tools["delete_task"]["requires_approval"] and tools["delete_task"]["risk"] == "consequential"
    assert tools["get_bills"]["permission"] == "finance:read" and "properties" in tools["create_task"]["input_schema"]


def test_backend_compat_complete_endpoint(client):
    body = {"system": "Today is 2026-09-28.", "messages": [{"role": "user", "content": "What bills are due this week?"}],
            "tools": [{"name": "get_bills", "description": "List bills", "input_schema": {"type": "object"}}]}
    r = client.post("/v1/complete", json=body, headers={"Authorization": f"Bearer {SERVICE_TOKEN}"})
    assert r.status_code == 200
    data = r.json()
    assert data["stop_reason"] == "tool_use" and data["content"][1]["name"] == "get_bills"
    assert client.post("/v1/complete", json=body).status_code == 401


def test_secrets_never_reach_logs(client, caplog):
    caplog.set_level(logging.DEBUG)
    client.post("/agent/run", json={"message": "What bills are due this week?"}, headers=AUTH)
    client.post("/agent/run", json={"message": "hi"}, headers={**AUTH, "X-User-Authorization": "Bearer nope"})
    logged = "\n".join(r.getMessage() + str(r.__dict__) for r in caplog.records)
    for secret in (SERVICE_TOKEN, TOKEN_A, "sk-ant-never-log-me-123456"):
        assert secret not in logged


def test_execute_action_runs_an_approved_payload(client, backend):
    body = {"action_type": "create_task", "action_payload": {"title": "Approved via backend", "category": "academic"}}
    r = client.post("/agent/actions/execute", json=body, headers=AUTH)
    assert r.status_code == 200 and r.json()["status"] == "completed"
    assert r.json()["result"]["title"] == "Approved via backend"
    assert backend.data[USER_A]["tasks"][-1]["title"] == "Approved via backend"


def test_execute_action_guards(client, backend):
    before = len(backend.data[USER_A]["tasks"])
    no_service = client.post("/agent/actions/execute", json={"action_type": "create_task", "action_payload": {"title": "x"}},
                             headers={"X-User-Authorization": f"Bearer {TOKEN_A}"})
    assert no_service.status_code == 401
    assert client.post("/agent/actions/execute", json={"action_type": "launch_rockets"}, headers=AUTH).status_code == 404
    bad = client.post("/agent/actions/execute", json={"action_type": "create_task", "action_payload": {"title": ""}}, headers=AUTH)
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "INVALID_REQUEST"
    gone = client.post("/agent/actions/execute", json={"action_type": "delete_task", "action_payload": {"task_id": "missing"}}, headers=AUTH)
    assert gone.status_code == 409
    assert len(backend.data[USER_A]["tasks"]) == before
