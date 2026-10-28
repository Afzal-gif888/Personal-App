"""Tenant isolation tests for Agent Core with forwarded user JWTs."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import SERVICE_TOKEN, make_settings
from tests.fakes import TOKEN_A, TOKEN_B, USER_A, USER_B
from tests.mock_llm import MockLLMProvider


@pytest.fixture
def client(backend):
    app = create_app(
        make_settings(agent_core_service_token=SERVICE_TOKEN, llm_api_key="sk-test-isolation-123"),
        llm=MockLLMProvider(),
        backend_transport=backend.transport(),
    )
    with TestClient(app) as c:
        yield c


def test_user_b_cannot_spoof_user_a_id_in_run(client):
    """Passing User A's user_id with User B's token is immediately rejected with 403."""
    headers = {
        "Authorization": f"Bearer {SERVICE_TOKEN}",
        "X-User-Authorization": f"Bearer {TOKEN_B}",
    }
    resp = client.post("/agent/run", json={"message": "List my tasks", "user_id": USER_A}, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_user_b_token_cannot_execute_action_on_user_a_task(client, backend):
    """User B's forwarded token cannot modify or delete User A's task via /agent/actions/execute."""
    # Seed User A with a confidential task
    task_a = backend.add(USER_A, "tasks", title="User A Private Thesis", category="academic")
    task_id = task_a["id"]

    headers_b = {
        "Authorization": f"Bearer {SERVICE_TOKEN}",
        "X-User-Authorization": f"Bearer {TOKEN_B}",
    }
    payload = {
        "action_type": "delete_task",
        "action_payload": {"task_id": task_id},
    }
    resp = client.post("/agent/actions/execute", json=payload, headers=headers_b)
    # Backend rejects because User B does not own task_id
    assert resp.status_code in (404, 409, 422)

    # Verify task still exists in User A's store
    assert any(t["id"] == task_id for t in backend.data[USER_A]["tasks"])


def test_user_b_token_cannot_read_user_a_documents_via_search(client, backend):
    """User B's forwarded token cannot retrieve User A's indexed documents."""
    backend.add_document(USER_A, "secret_ml.pdf", "Overfitting and regularization research.")

    headers_b = {
        "Authorization": f"Bearer {SERVICE_TOKEN}",
        "X-User-Authorization": f"Bearer {TOKEN_B}",
    }
    resp = client.post(
        "/agent/run",
        json={"message": "What does my document say about overfitting?", "user_id": USER_B},
        headers=headers_b,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Search tool executed with User B's token returned no chunks from User A
    for tc in data.get("tool_calls", []):
        if tc["name"] == "search_documents":
            assert tc["output"].get("chunks", []) == []
