from datetime import date

from tests.test_agent import new_conversation, send


def add_expense(client, auth, amount, category, day=None):
    resp = client.post(
        "/api/v1/expenses",
        headers=auth,
        json={"title": "x", "amount": amount, "category": category, "expenseDate": (day or date.today()).isoformat()},
    )
    assert resp.status_code == 201, resp.text


def test_budget_progress_and_statuses(client, auth):
    food = client.post("/api/v1/budgets", headers=auth, json={"category": "food", "amount": 1000})
    assert food.status_code == 201, food.text
    body = food.json()
    assert body["spent"] == 0 and body["remaining"] == 1000 and body["status"] == "on_track"
    assert body["currency"] == "INR" and body["alertThreshold"] == 80 and body["month"] == f"{date.today():%Y-%m}"

    client.post("/api/v1/budgets", headers=auth, json={"amount": 2000})  # overall
    client.post("/api/v1/budgets", headers=auth, json={"category": "travel", "amount": 100})

    add_expense(client, auth, 850, "food")
    add_expense(client, auth, 150, "travel")
    add_expense(client, auth, 999, "food", day=date(2020, 1, 15))  # another month: not counted

    items = client.get("/api/v1/budgets", headers=auth).json()
    assert [b["category"] for b in items] == [None, "food", "travel"]  # overall first
    overall, food, travel = items
    assert (overall["spent"], overall["percentUsed"], overall["status"]) == (1000, 50, "on_track")
    assert (food["spent"], food["remaining"], food["status"]) == (850, 150, "warning")
    assert (travel["spent"], travel["remaining"], travel["status"]) == (150, 0, "over")

    past = client.get("/api/v1/budgets?month=2020-01", headers=auth).json()
    assert [b["spent"] for b in past] == [999, 999, 0]


def test_budget_validation_update_and_isolation(client, auth, other_auth):
    assert client.post("/api/v1/budgets", headers=auth, json={"category": "food", "amount": 0}).status_code == 422
    assert client.post("/api/v1/budgets", headers=auth, json={"category": "nope", "amount": 5}).status_code == 422

    budget = client.post("/api/v1/budgets", headers=auth, json={"category": "food", "amount": 500}).json()
    dup = client.post("/api/v1/budgets", headers=auth, json={"category": "food", "amount": 700})
    assert dup.status_code == 409
    client.post("/api/v1/budgets", headers=auth, json={"amount": 5000})
    assert client.post("/api/v1/budgets", headers=auth, json={"amount": 6000}).status_code == 409

    upd = client.patch(f"/api/v1/budgets/{budget['id']}", headers=auth, json={"amount": 750, "alertThreshold": 90})
    assert upd.status_code == 200 and upd.json()["amount"] == 750 and upd.json()["alertThreshold"] == 90
    assert client.patch(f"/api/v1/budgets/{budget['id']}", headers=auth, json={"amount": None}).status_code == 422

    assert client.get("/api/v1/budgets", headers=other_auth).json() == []
    assert client.delete(f"/api/v1/budgets/{budget['id']}", headers=other_auth).status_code == 404
    assert client.delete(f"/api/v1/budgets/{budget['id']}", headers=auth).status_code == 204
    assert len(client.get("/api/v1/budgets", headers=auth).json()) == 1


def test_agent_sets_budget_only_after_approval(client, auth):
    conv = new_conversation(client, auth)
    msg = send(client, auth, conv, "Set my food budget to 3000")["assistantMessage"]
    [action] = msg["metadata"]["actions"]
    assert action["action"] == "set_budget" and action["status"] == "pending"
    assert client.get("/api/v1/budgets", headers=auth).json() == []

    assert client.post(f"/api/v1/approvals/{action['approvalId']}/approve", headers=auth).status_code == 200
    [budget] = client.get("/api/v1/budgets", headers=auth).json()
    assert budget["category"] == "food" and budget["amount"] == 3000

    # A second proposal for the same category updates the limit instead of failing.
    action = send(client, auth, conv, "Change my food budget limit to 2500")["assistantMessage"]["metadata"]["actions"][0]
    assert action["actionLabel"] == "Update budget"
    client.post(f"/api/v1/approvals/{action['approvalId']}/approve", headers=auth)
    [budget] = client.get("/api/v1/budgets", headers=auth).json()
    assert budget["amount"] == 2500


def test_agent_reports_budget_status(client, auth):
    client.post("/api/v1/budgets", headers=auth, json={"category": "food", "amount": 100})
    add_expense(client, auth, 120, "food")
    out = send(client, auth, new_conversation(client, auth), "How are my budgets looking?")
    msg = out["assistantMessage"]
    assert [s["toolName"] for s in msg["metadata"]["steps"]] == ["get_budget_status"]
    assert "over budget" in msg["content"]
