"""An in-memory stand-in for the AgentOS backend API, served through httpx.MockTransport.

It implements the endpoints the Agent Core uses with the same paths, camelCase JSON and error
shape as the real backend, scoped per access token, so tools and flows are tested end to end
without PostgreSQL.
"""

import json
import re
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

TOKEN_A = "token-user-a"
TOKEN_B = "token-user-b"
USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(UTC).isoformat()


def err(status: int, code: str, message: str, details=None) -> httpx.Response:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return httpx.Response(status, json=body)


class FakeBackend:
    def __init__(self, today: date | None = None) -> None:
        self.today = today or date.today()
        self.users = {
            TOKEN_A: {"id": USER_A, "name": "Asha", "email": "asha@example.com"},
            TOKEN_B: {"id": USER_B, "name": "Ben", "email": "ben@example.com"},
        }
        self.prefs: dict[str, dict[str, Any]] = {
            USER_A: {"dailyStudyGoalMinutes": 120, "preferredStudyStart": "18:00", "preferredStudyEnd": "22:00",
                     "defaultReminderTime": "09:00", "timezone": "Asia/Kolkata", "currency": "INR",
                     "notificationPreferences": {}},
            USER_B: {"dailyStudyGoalMinutes": 60, "preferredStudyStart": None, "preferredStudyEnd": None,
                     "defaultReminderTime": "08:00", "timezone": "UTC", "currency": "INR", "notificationPreferences": {}},
        }
        self.data: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self.files: dict[str, bytes] = {}
        self.messages: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.calls: list[tuple[str, str]] = []
        self.fail: dict[str, int] = {}  # path regex -> status code to return
        self.healthy = True

    # --- seeding helpers ---

    def add(self, user: str, kind: str, **fields: Any) -> dict[str, Any]:
        item = {"id": _id(), "createdAt": _now(), "updatedAt": _now(), **fields}
        self.data[user][kind].append(item)
        return item

    def add_document(self, user: str, name: str, text: str, mime: str = "text/plain") -> dict[str, Any]:
        doc = self.add(user, "documents", name=name, mimeType=mime, size=len(text.encode()), category="notes",
                       status="ready", pageCount=None, errorMessage=None, uploadedAt=_now(), processedAt=_now(),
                       downloadUrl="")
        self.files[doc["id"]] = text.encode()
        return doc

    def seed_student(self, user: str = USER_A) -> None:
        t = self.today
        self.add(user, "subjects", name="Machine Learning", code="ML", description=None, color=None)
        self.add(user, "subjects", name="Database Management Systems", code="DBMS", description=None, color=None)
        self.add(user, "tasks", title="ML assignment 3", description=None, category="academic", priority="high",
                 status="pending", dueDate=(t + timedelta(days=2)).isoformat(), dueTime=None, subjectId=None,
                 subject="Machine Learning", completedAt=None)
        self.add(user, "tasks", title="DBMS assignment", description=None, category="academic", priority="medium",
                 status="pending", dueDate=(t + timedelta(days=4)).isoformat(), dueTime=None, subjectId=None,
                 subject="Database Management Systems", completedAt=None)
        self.add(user, "tasks", title="Update resume", description=None, category="career", priority="low",
                 status="pending", dueDate=None, dueTime=None, subjectId=None, subject=None, completedAt=None)
        day = (t + timedelta(days=1)).isoformat()
        self.add(user, "events", title="ML lecture", description=None, eventType="class",
                 startAt=f"{day}T04:30:00+00:00", endAt=f"{day}T05:30:00+00:00", date=day, startTime="10:00",
                 endTime="11:00", location="Room 101", meetingUrl=None, notes=None)
        self.add(user, "bills", title="Electricity bill", category="electricity", amount=1200.0, currency="INR",
                 dueDate=(t + timedelta(days=3)).isoformat(), status="upcoming", recurring=True, frequency="monthly",
                 paymentMethod=None, notes=None)
        self.add(user, "bills", title="Hostel rent", category="hostel", amount=8000.0, currency="INR",
                 dueDate=(t + timedelta(days=20)).isoformat(), status="upcoming", recurring=True, frequency="monthly",
                 paymentMethod=None, notes=None)
        self.add(user, "reminders", title="Review study plan", description=None, category="academic",
                 scheduledAt=f"{day}T03:30:00+00:00", date=day, time="09:00", repeatRule="weekly", status="pending",
                 completedAt=None)
        self.add(user, "goals", title="Land a summer internship", description=None, category="career",
                 targetValue=None, currentValue=None, unit=None, manualProgress=40, progress=40, deadline=None,
                 status="active")
        self.add(user, "goals", title="Save ₹20,000", description=None, category="financial", targetValue=20000.0,
                 currentValue=5000.0, unit="INR", manualProgress=None, progress=25, deadline=None, status="active")
        self.add(user, "subscriptions", name="Spotify", amount=119.0, currency="INR", billingCycle="monthly",
                 nextBillingDate=(t + timedelta(days=5)).isoformat(), status="active", notes=None)
        self.add(user, "expenses", title="Groceries", description=None, category="food", amount=850.0, currency="INR",
                 expenseDate=t.isoformat(), paymentMethod="UPI")
        self.add(user, "expenses", title="Metro card", description=None, category="travel", amount=300.0,
                 currency="INR", expenseDate=t.isoformat(), paymentMethod="UPI")

    # --- transport ---

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append((request.method, path))
        if path == "/health":
            return httpx.Response(200 if self.healthy else 503, json={"status": "ok"})
        for pattern, status in self.fail.items():
            if re.search(pattern, path):
                return err(status, "INTERNAL_ERROR", "An unexpected error occurred")
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        user = self.users.get(token)
        if user is None:
            return err(401, "INVALID_TOKEN", "Invalid token")
        body = json.loads(request.content) if request.content else {}
        route = path.removeprefix("/api/v1")
        return self.route(request.method, route, dict(request.url.params.multi_items()),
                          request.url.params, body, user["id"], user)

    def route(self, method, route, params, multi, body, uid, user) -> httpx.Response:
        d = self.data[uid]
        m = re.fullmatch

        if route == "/users/me" and method == "GET":
            return httpx.Response(200, json={**user, "avatarUrl": None, "university": None, "major": None,
                                             "academicYear": None, "bio": None, "createdAt": _now()})
        if route == "/users/me/preferences":
            if method == "PATCH":
                self.prefs[uid].update(body)
            return httpx.Response(200, json=self.prefs[uid])
        if g := m(r"/conversations/([^/]+)/messages", route):
            return httpx.Response(200, json=self.messages.get(g.group(1), []))

        # tasks
        if route == "/tasks" and method == "GET":
            items = d["tasks"]
            if statuses := multi.get_list("status"):
                items = [t for t in items if t["status"] in statuses]
            for key in ("priority", "category"):
                if params.get(key):
                    items = [t for t in items if t[key] == params[key]]
            if q := params.get("q"):
                words = q.lower().split()
                items = [t for t in items if any(w in t["title"].lower() for w in words)]
            if due_to := params.get("due_to"):
                items = [t for t in items if t["dueDate"] and t["dueDate"] <= due_to]
            size = int(params.get("page_size", 50))
            return httpx.Response(200, json={"items": items[:size], "total": len(items), "page": 1, "pageSize": size})
        if route == "/tasks" and method == "POST":
            if not body.get("title"):
                return err(422, "VALIDATION_ERROR", "Request validation failed", [{"field": "title"}])
            return httpx.Response(201, json=self.add(uid, "tasks", **{"description": None, "category": "general",
                                  "priority": "medium", "status": "pending", "dueDate": None, "dueTime": None,
                                  "subjectId": None, "subject": None, "completedAt": None, **body}))
        if g := m(r"/tasks/([^/]+)", route):
            return self._item(d, "tasks", g.group(1), method, body)

        if route == "/subjects" and method == "POST":
            return httpx.Response(201, json=self.add(uid, "subjects", **{"code": None, "description": None, "color": None, **body}))
        if route == "/subjects":
            return httpx.Response(200, json=d["subjects"])
        if route == "/budgets" and method == "GET":
            month = params.get("month") or self.today.strftime("%Y-%m")
            out = []
            for b in d["budgets"]:
                spent = sum(e["amount"] for e in d["expenses"] if e["expenseDate"].startswith(month)
                            and (b["category"] is None or e["category"] == b["category"]))
                pct = int(spent * 100 / b["amount"]) if b["amount"] else 0
                out.append({**b, "month": month, "spent": spent, "remaining": b["amount"] - spent, "percentUsed": pct,
                            "status": "over" if pct >= 100 else "warning" if pct >= b["alertThreshold"] else "on_track"})
            return httpx.Response(200, json=out)
        if route == "/budgets" and method == "POST":
            b = self.add(uid, "budgets", **{"category": None, "alertThreshold": 80, "currency": "INR", **body})
            return httpx.Response(201, json={**b, "month": self.today.strftime("%Y-%m"), "spent": 0, "remaining": b["amount"],
                                             "percentUsed": 0, "status": "on_track"})
        if g := m(r"/budgets/([^/]+)", route):
            item = self._find(d, "budgets", g.group(1))
            if item is None:
                return err(404, "NOT_FOUND", "Budget not found")
            item.update(body)
            return httpx.Response(200, json={**item, "month": self.today.strftime("%Y-%m"), "spent": 0,
                                             "remaining": item["amount"], "percentUsed": 0, "status": "on_track"})

        # study
        if route == "/study-plans/generate" and method == "POST":
            start = date.fromisoformat(body.get("startDate") or (self.today + timedelta(days=1)).isoformat())
            sessions = [{"topic": f"{body['subject']} - part {i + 1}", "date": (start + timedelta(days=i)).isoformat(),
                         "startTime": "18:00", "endTime": "19:00", "priority": "medium", "subjectName": body["subject"]}
                        for i in range(body.get("days", 5))]
            return httpx.Response(200, json={"title": f"{body['subject']} study plan", "description": None,
                                             "startDate": start.isoformat(),
                                             "endDate": (start + timedelta(days=body.get("days", 5) - 1)).isoformat(),
                                             "status": "active", "sessions": sessions})
        if route == "/study-plans" and method == "GET":
            return httpx.Response(200, json=[p for p in d["study_plans"] if not params.get("status") or p["status"] == params["status"]])
        if route == "/study-plans" and method == "POST":
            fields = {"status": "active", **{k: v for k, v in body.items() if k != "sessions"}}
            plan = self.add(uid, "study_plans", **fields)
            plan["sessions"] = [
                self.add(uid, "study_sessions", **{"studyPlanId": plan["id"], "subjectId": None, "status": "scheduled",
                                                   "description": None, **s})
                for s in body.get("sessions", [])
            ]
            return httpx.Response(201, json=plan)
        if g := m(r"/study-plans/([^/]+)", route):
            return self._item(d, "study_plans", g.group(1), method, body)
        if route == "/study-sessions" and method == "GET":
            return httpx.Response(200, json=d["study_sessions"])
        if route == "/study-sessions" and method == "POST":
            return httpx.Response(201, json=self.add(uid, "study_sessions", **{"studyPlanId": None, "subjectId": None,
                                                     "status": "scheduled", "description": None, **body}))
        if g := m(r"/study-sessions/([^/]+)", route):
            return self._item(d, "study_sessions", g.group(1), method, body)

        # events
        if route == "/events" and method == "GET":
            items = [e for e in d["events"] if (not params.get("start") or e["date"] >= params["start"])
                     and (not params.get("end") or e["date"] <= params["end"])]
            return httpx.Response(200, json=items)
        if route == "/events" and method == "POST":
            start = f"{body['date']}T{body['startTime'][:5]}:00+00:00"
            return httpx.Response(201, json=self.add(uid, "events", **{**dict(description=None, location=None, meetingUrl=None,
                                                     notes=None, eventType="general", endTime=None, startAt=start,
                                                     endAt=None), **body}))
        if g := m(r"/events/([^/]+)", route):
            return self._item(d, "events", g.group(1), method, body)

        # reminders
        if route == "/reminders" and method == "GET":
            statuses = multi.get_list("status")
            return httpx.Response(200, json=[r for r in d["reminders"] if not statuses or r["status"] in statuses])
        if route == "/reminders" and method == "POST":
            return httpx.Response(201, json=self.add(uid, "reminders", **{**dict(description=None, category="general",
                                                     repeatRule="none", status="pending", completedAt=None,
                                                     scheduledAt=f"{body['date']}T{body['time'][:5]}:00+00:00"), **body}))
        if g := m(r"/reminders/([^/]+)/(complete|snooze)", route):
            item = self._find(d, "reminders", g.group(1))
            if item is None:
                return err(404, "NOT_FOUND", "Reminder not found")
            item["status"] = "completed" if g.group(2) == "complete" else "snoozed"
            return httpx.Response(200, json=item)
        if g := m(r"/reminders/([^/]+)", route):
            return self._item(d, "reminders", g.group(1), method, body)

        # finance
        if route == "/bills" and method == "GET":
            statuses = multi.get_list("status")
            items = [b for b in d["bills"] if (not statuses or b["status"] in statuses)
                     and (not params.get("due_to") or b["dueDate"] <= params["due_to"])]
            return httpx.Response(200, json=items)
        if route == "/bills" and method == "POST":
            return httpx.Response(201, json=self.add(uid, "bills", **{**dict(currency="INR", status="upcoming", recurring=False,
                                                     frequency=None, paymentMethod=None, notes=None, category="other"), **body}))
        if g := m(r"/bills/([^/]+)/pay", route):
            bill = self._find(d, "bills", g.group(1))
            if bill is None:
                return err(404, "NOT_FOUND", "Bill not found")
            bill["status"] = "paid"
            pay = self.add(uid, "payments", billId=bill["id"], paymentPlanId=None, amount=body.get("amount", bill["amount"]),
                           currency="INR", paymentDate=body.get("paymentDate", self.today.isoformat()),
                           paymentMethod=body.get("paymentMethod"), status="completed", notes=None)
            return httpx.Response(200, json={"bill": bill, "payment": pay, "nextBill": None})
        if g := m(r"/bills/([^/]+)", route):
            return self._item(d, "bills", g.group(1), method, body)
        if route == "/payments":
            return httpx.Response(200, json={"items": d["payments"], "total": len(d["payments"]), "page": 1, "pageSize": 50})
        if route == "/payment-plans" and method == "GET":
            return httpx.Response(200, json=[p for p in d["payment_plans"] if not params.get("status") or p["status"] == params["status"]])
        if route == "/payment-plans" and method == "POST":
            n = max(1, round(body["totalAmount"] / body["installmentAmount"]))
            return httpx.Response(201, json=self.add(uid, "payment_plans", **{"currency": "INR", "nextPaymentDate": body["startDate"],
                                                     "remainingAmount": body["totalAmount"], "totalInstallments": n,
                                                     "completedInstallments": 0, "status": "active", **body}))
        if route == "/expenses/summary":
            month = params.get("month") or self.today.strftime("%Y-%m")
            items = [e for e in d["expenses"] if e["expenseDate"].startswith(month)]
            cats: dict[str, list[float]] = defaultdict(list)
            for e in items:
                cats[e["category"]].append(e["amount"])
            return httpx.Response(200, json={"month": month, "currency": "INR", "total": sum(e["amount"] for e in items),
                                             "count": len(items), "byCategory": [{"category": c, "total": sum(v), "count": len(v)} for c, v in cats.items()]})
        if route == "/expenses" and method == "GET":
            return httpx.Response(200, json={"items": d["expenses"], "total": len(d["expenses"]), "page": 1, "pageSize": 50})
        if route == "/expenses" and method == "POST":
            return httpx.Response(201, json=self.add(uid, "expenses", **{**dict(currency="INR", description=None, category="other",
                                                     paymentMethod=None), **body}))
        if route == "/subscriptions" and method == "GET":
            return httpx.Response(200, json=[s for s in d["subscriptions"] if not params.get("status") or s["status"] == params["status"]])
        if g := m(r"/subscriptions/([^/]+)", route):
            return self._item(d, "subscriptions", g.group(1), method, body)
        if route == "/subscriptions" and method == "POST":
            return httpx.Response(201, json=self.add(uid, "subscriptions", **{**dict(currency="INR", billingCycle="monthly",
                                                     nextBillingDate=None, status="active", notes=None), **body}))

        # goals
        if route == "/goals" and method == "GET":
            return httpx.Response(200, json=[g_ for g_ in d["goals"] if (not params.get("status") or g_["status"] == params["status"])
                                             and (not params.get("category") or g_["category"] == params["category"])])
        if route == "/goals" and method == "POST":
            return httpx.Response(201, json=self.add(uid, "goals", **{**dict(description=None, category="general", targetValue=None,
                                                     currentValue=None, unit=None, manualProgress=None, progress=0,
                                                     deadline=None, status="active"), **body}))
        if g := m(r"/goals/([^/]+)", route):
            resp = self._item(d, "goals", g.group(1), method, body)
            item = self._find(d, "goals", g.group(1))
            if item and "manualProgress" in body:
                item["progress"] = body["manualProgress"]
                resp = httpx.Response(200, json=item)
            return resp

        # documents
        if route == "/documents":
            items = [x for x in d["documents"] if not params.get("status") or x["status"] == params["status"]]
            if q := params.get("q"):
                items = [x for x in items if q.lower() in x["name"].lower()]
            return httpx.Response(200, json={"items": items, "total": len(items), "page": 1, "pageSize": 50})
        if route == "/documents/search" and method == "POST":
            return self._search_documents(d, body)
        if g := m(r"/documents/([^/]+)", route):
            return self._item(d, "documents", g.group(1), method, body)

        return err(404, "NOT_FOUND", f"No route {method} {route}")

    def _search_documents(self, d, body: dict[str, Any]) -> httpx.Response:
        """Stand-in for the backend's pgvector search: word overlap over this user's documents only
        (the real ranking is semantic; that is tested in the backend against PostgreSQL + Gemini)."""
        def words(text: str) -> set[str]:
            return {w[:6] for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 3}

        query = words(body.get("query", ""))
        allowed = set(body.get("documentIds") or []) or None
        hits = []
        for doc in d["documents"]:
            if allowed and doc["id"] not in allowed:
                continue
            paragraphs = [p for p in self.files.get(doc["id"], b"").decode().split("\n\n") if p.strip()]
            for i, para in enumerate(paragraphs):
                score = len(query & words(para)) / max(len(query), 1)
                if score > 0:
                    hits.append({"chunkId": f"{doc['id']}:{i}", "documentId": doc["id"], "documentName": doc["name"],
                                 "chunkIndex": i, "pageNumber": None, "content": para, "similarity": round(score, 3)})
        hits.sort(key=lambda h: -h["similarity"])
        hits = hits[: body.get("topK") or 5]
        return httpx.Response(200, json={"query": body.get("query"), "results": hits,
                                         "message": None if hits else "No relevant document content found."})

    @staticmethod
    def _find(d, kind: str, item_id: str) -> dict[str, Any] | None:
        return next((x for x in d[kind] if x["id"] == item_id), None)

    def _item(self, d, kind: str, item_id: str, method: str, body: dict[str, Any]) -> httpx.Response:
        item = self._find(d, kind, item_id)
        if item is None:
            return err(404, "NOT_FOUND", f"{kind[:-1].title()} not found")
        if method == "GET":
            return httpx.Response(200, json=item)
        if method == "PATCH":
            item.update(body)
            if body.get("status") == "completed" and kind == "tasks":
                item["completedAt"] = _now()
            return httpx.Response(200, json=item)
        if method == "DELETE":
            d[kind].remove(item)
            return httpx.Response(204)
        return err(405, "METHOD_NOT_ALLOWED", "Method not allowed")
