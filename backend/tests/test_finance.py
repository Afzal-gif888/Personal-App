from datetime import date, timedelta


def test_bill_status_pay_and_recurrence(client, auth):
    past = (date.today() - timedelta(days=10)).isoformat()
    bill = client.post(
        "/api/v1/bills",
        headers=auth,
        json={"title": "Phone", "amount": "499.00", "dueDate": past, "recurring": True, "frequency": "monthly", "category": "phone"},
    ).json()
    assert bill["status"] == "overdue" and bill["amount"] == 499.0 and bill["currency"] == "INR"

    paid = client.post(f"/api/v1/bills/{bill['id']}/pay", headers=auth, json={"paymentMethod": "UPI"})
    assert paid.status_code == 200, paid.text
    body = paid.json()
    assert body["bill"]["status"] == "paid"
    assert body["payment"]["amount"] == 499.0 and body["payment"]["paymentMethod"] == "UPI"
    assert body["nextBill"]["dueDate"] > past

    assert client.post(f"/api/v1/bills/{bill['id']}/pay", headers=auth).status_code == 409
    assert client.get("/api/v1/payments", headers=auth).json()["total"] == 1

    no_freq = client.post("/api/v1/bills", headers=auth, json={"title": "x", "amount": 1, "dueDate": past, "recurring": True})
    assert no_freq.status_code == 422


def test_payment_plan_installments(client, auth):
    plan = client.post(
        "/api/v1/payment-plans",
        headers=auth,
        json={"title": "Laptop EMI", "totalAmount": 30000, "installmentAmount": 10000, "startDate": "2026-10-01"},
    ).json()
    assert plan["totalInstallments"] == 3 and plan["remainingAmount"] == 30000.0

    for _ in range(3):
        plan = client.post(f"/api/v1/payment-plans/{plan['id']}/payments", headers=auth).json()
    assert plan["status"] == "completed" and plan["remainingAmount"] == 0 and plan["nextPaymentDate"] is None
    assert client.post(f"/api/v1/payment-plans/{plan['id']}/payments", headers=auth).status_code == 409


def test_expense_summary_by_category(client, auth):
    for title, cat, amount in [("Lunch", "food", 120), ("Dinner", "food", 250.5), ("Bus", "travel", 40)]:
        client.post("/api/v1/expenses", headers=auth, json={"title": title, "category": cat, "amount": amount, "expenseDate": "2026-09-15"})
    client.post("/api/v1/expenses", headers=auth, json={"title": "Old", "amount": 999, "expenseDate": "2026-08-31"})

    summary = client.get("/api/v1/expenses/summary", headers=auth, params={"month": "2026-09"}).json()
    assert summary["total"] == 410.5 and summary["count"] == 3
    assert summary["byCategory"][0] == {"category": "food", "total": 370.5, "count": 2}

    page = client.get("/api/v1/expenses", headers=auth, params={"category": "food", "page_size": 1}).json()
    assert page["total"] == 2 and len(page["items"]) == 1

    assert client.post("/api/v1/expenses", headers=auth, json={"title": "x", "amount": -5, "expenseDate": "2026-09-01"}).status_code == 422


def test_dashboard_summary(client, auth):
    today = date.today().isoformat()
    client.post("/api/v1/tasks", headers=auth, json={"title": "Due now", "dueDate": today})
    client.post("/api/v1/bills", headers=auth, json={"title": "Wifi", "amount": 800, "dueDate": today})
    dash = client.get("/api/v1/dashboard", headers=auth)
    assert dash.status_code == 200, dash.text
    body = dash.json()
    assert body["stats"]["openTasks"] == 1
    assert body["stats"]["upcomingBillsTotal"] == 800.0
    assert body["upcomingBills"][0]["title"] == "Wifi"
