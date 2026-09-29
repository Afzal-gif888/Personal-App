from datetime import date, timedelta

import pytest

from app.llm import LLMError, LLMResponse
from app.services import chat as chat_service


def new_conversation(client, auth) -> str:
    resp = client.post("/api/v1/conversations", headers=auth, json={})
    assert resp.status_code == 201
    return resp.json()["id"]


def send(client, auth, conversation_id, text):
    resp = client.post(f"/api/v1/conversations/{conversation_id}/messages", headers=auth, json={"content": text})
    assert resp.status_code == 201, resp.text
    return resp.json()


class ScriptedProvider:
    """Returns canned responses in order, recording what it was sent."""

    name = "scripted"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, *, system, messages, tools):
        self.calls.append(list(messages))  # snapshot: the runner keeps appending to the same list
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


def tool_call(name, args, id_="toolu_1"):
    return LLMResponse(content=[{"type": "tool_use", "id": id_, "name": name, "input": args}], stop_reason="tool_use")


def text(t):
    return LLMResponse(content=[{"type": "text", "text": t}], stop_reason="end_turn")


def test_reminder_is_proposed_not_created_until_approved(client, auth):
    conv = new_conversation(client, auth)
    out = send(client, auth, conv, "Remind me to call mom tomorrow at 7pm")

    msg = out["assistantMessage"]
    assert msg["metadata"]["status"] == "success"
    [action] = msg["metadata"]["actions"]
    assert action["status"] == "pending" and action["details"]["Time"] == "19:00"
    assert "approval" in msg["content"].lower()
    assert out["agentRun"]["status"] == "waiting_for_approval"
    assert out["conversation"]["title"].startswith("Remind me to call mom")

    # Nothing was written yet.
    assert client.get("/api/v1/reminders", headers=auth).json() == []

    approved = client.post(f"/api/v1/approvals/{action['approvalId']}/approve", headers=auth)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved" and approved.json()["result"]["resource_type"] == "reminder"

    [reminder] = client.get("/api/v1/reminders", headers=auth).json()
    assert reminder["title"] == "Call mom" and reminder["time"] == "19:00"

    # The transcript, run and notifications reflect the decision.
    messages = client.get(f"/api/v1/conversations/{conv}/messages", headers=auth).json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["metadata"]["actions"][0]["status"] == "approved"
    run = client.get(f"/api/v1/agent-runs/{out['agentRun']['id']}", headers=auth).json()
    assert run["status"] == "completed"
    assert run["toolCalls"][0]["toolName"] == "create_reminder" and run["toolCalls"][0]["status"] == "completed"
    assert client.get("/api/v1/notifications/unread-count", headers=auth).json()["unread"] == 1

    again = client.post(f"/api/v1/approvals/{action['approvalId']}/approve", headers=auth)
    assert again.status_code == 409 and again.json()["error"]["code"] == "APPROVAL_NOT_PENDING"


def test_bill_question_reads_then_proposes_and_reject_discards(client, auth):
    due = (date.today() + timedelta(days=5)).isoformat()
    client.post("/api/v1/bills", headers=auth, json={"title": "Electricity", "amount": 1200, "dueDate": due, "category": "electricity"})
    conv = new_conversation(client, auth)
    out = send(client, auth, conv, "What bills do I need to pay?")

    steps = out["assistantMessage"]["metadata"]["steps"]
    assert [s["toolName"] for s in steps] == ["list_bills", "create_reminder"]
    assert "Electricity" in out["assistantMessage"]["content"]
    [action] = out["assistantMessage"]["metadata"]["actions"]

    rejected = client.post(f"/api/v1/approvals/{action['approvalId']}/reject", headers=auth, json={"reason": "not now"})
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert client.get("/api/v1/reminders", headers=auth).json() == []
    assert client.get(f"/api/v1/agent-runs/{out['agentRun']['id']}", headers=auth).json()["status"] == "completed"


def test_study_plan_proposal_saves_exactly_the_previewed_sessions(client, auth):
    conv = new_conversation(client, auth)
    out = send(client, auth, conv, "Make a study plan for my Database Systems exam")
    [action] = out["assistantMessage"]["metadata"]["actions"]
    assert action["action"] == "create_study_plan"
    preview = action["details"]
    assert preview["Subject"] == "Database Systems" and preview["Sessions"] == len(preview["Schedule"])

    client.post(f"/api/v1/approvals/{action['approvalId']}/approve", headers=auth)
    [plan] = client.get("/api/v1/study-plans", headers=auth).json()
    assert len(plan["sessions"]) == preview["Sessions"]


def test_other_users_cannot_decide_approvals(client, auth, other_auth):
    conv = new_conversation(client, auth)
    action = send(client, auth, conv, "Remind me to stretch today at 6pm")["assistantMessage"]["metadata"]["actions"][0]
    assert client.post(f"/api/v1/approvals/{action['approvalId']}/approve", headers=other_auth).status_code == 404
    assert client.get(f"/api/v1/conversations/{conv}/messages", headers=other_auth).status_code == 404


def test_history_is_sent_to_the_model(client, auth, monkeypatch):
    provider = ScriptedProvider(text("Hi!"), text("You said hello."))
    monkeypatch.setattr(chat_service, "get_provider", lambda: provider)
    conv = new_conversation(client, auth)
    send(client, auth, conv, "hello")
    send(client, auth, conv, "what did I say?")
    assert provider.calls[1][:3] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "Hi!"},
        {"role": "user", "content": "what did I say?"},
    ]


def test_llm_failure_is_reported_in_the_transcript(client, auth, monkeypatch):
    monkeypatch.setattr(chat_service, "get_provider", lambda: ScriptedProvider(LLMError("The assistant is busy.", retryable=True)))
    conv = new_conversation(client, auth)
    out = send(client, auth, conv, "hello")
    assert out["assistantMessage"]["metadata"] == {"status": "error", "steps": [], "actions": [], "error": "The assistant is busy."}
    assert out["agentRun"]["status"] == "failed"


def test_invalid_tool_input_goes_back_to_the_model(client, auth, monkeypatch):
    provider = ScriptedProvider(
        tool_call("create_reminder", {"title": "x", "date": "not-a-date", "time": "10:00"}),
        text("Sorry, which date?"),
    )
    monkeypatch.setattr(chat_service, "get_provider", lambda: provider)
    out = send(client, auth, new_conversation(client, auth), "remind me")
    tool_result = provider.calls[1][-1]["content"][0]
    assert tool_result["is_error"] is True and "date" in tool_result["content"]
    assert out["assistantMessage"]["metadata"]["actions"] == []
    assert out["agentRun"]["status"] == "completed"


def test_stale_approval_stays_pending_when_apply_fails(client, auth, monkeypatch):
    bill = client.post(
        "/api/v1/bills", headers=auth, json={"title": "Rent", "amount": 9000, "dueDate": date.today().isoformat()}
    ).json()
    provider = ScriptedProvider(tool_call("mark_bill_paid", {"bill_id": bill["id"]}), text("Drafted."))
    monkeypatch.setattr(chat_service, "get_provider", lambda: provider)
    action = send(client, auth, new_conversation(client, auth), "I paid rent")["assistantMessage"]["metadata"]["actions"][0]
    assert action["details"]["Bill"] == "Rent"

    client.delete(f"/api/v1/bills/{bill['id']}", headers=auth)
    resp = client.post(f"/api/v1/approvals/{action['approvalId']}/approve", headers=auth)
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "APPROVAL_APPLY_FAILED"
    assert client.get(f"/api/v1/approvals/{action['approvalId']}", headers=auth).json()["status"] == "pending"
    assert client.post(f"/api/v1/approvals/{action['approvalId']}/reject", headers=auth).status_code == 200


def test_mark_bill_paid_rolls_recurring_bill(client, auth, monkeypatch):
    bill = client.post(
        "/api/v1/bills",
        headers=auth,
        json={"title": "Internet", "amount": 800, "dueDate": "2026-10-01", "recurring": True, "frequency": "monthly"},
    ).json()
    monkeypatch.setattr(
        chat_service, "get_provider", lambda: ScriptedProvider(tool_call("mark_bill_paid", {"bill_id": bill["id"]}), text("ok"))
    )
    action = send(client, auth, new_conversation(client, auth), "paid internet")["assistantMessage"]["metadata"]["actions"][0]
    result = client.post(f"/api/v1/approvals/{action['approvalId']}/approve", headers=auth).json()["result"]
    assert "next bill due 2026-11-01" in result["summary"]


@pytest.mark.parametrize("stop_reason", ["refusal"])
def test_refusal_is_handled(client, auth, monkeypatch, stop_reason):
    monkeypatch.setattr(
        chat_service, "get_provider", lambda: ScriptedProvider(LLMResponse(content=[], stop_reason=stop_reason))
    )
    out = send(client, auth, new_conversation(client, auth), "something")
    assert out["assistantMessage"]["content"] == "Sorry, I can't help with that request."


def test_unknown_tool_is_reported_to_model(client, auth, monkeypatch):
    provider = ScriptedProvider(tool_call("delete_everything", {}), text("I can't do that."))
    monkeypatch.setattr(chat_service, "get_provider", lambda: provider)
    send(client, auth, new_conversation(client, auth), "wipe it")
    assert provider.calls[1][-1]["content"][0]["is_error"] is True
