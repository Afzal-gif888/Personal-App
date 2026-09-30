"""HTTP client for the AgentOS FastAPI backend.

The Agent Core never talks to PostgreSQL. Every read and write goes through this client, which
calls the backend's public `/api/v1` API with the *user's own* access token, so the backend's
authorization rules decide what the agent can see and change.
"""

import logging
from datetime import date
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from app.backend import schemas as s
from app.backend.exceptions import (
    BackendAuthError,
    BackendError,
    BackendNotFoundError,
    BackendRateLimitError,
    BackendUnavailableError,
    BackendValidationError,
)

logger = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)


def _clean(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, date):
            value = value.isoformat()
        out[key] = value
    return out


class BackendClient:
    """One client per agent run, bound to one user's access token."""

    def __init__(
        self,
        base_url: str,
        access_token: str,
        *,
        timeout: float = 15.0,
        request_id: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        if request_id:
            headers["X-Request-ID"] = request_id
        self._http = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/api/v1", headers=headers, timeout=timeout, transport=transport
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "BackendClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    # --- transport ---------------------------------------------------------------------------------

    async def _request(self, method: str, path: str, *, params=None, json=None) -> Any:
        try:
            resp = await self._http.request(method, path, params=_clean(params or {}), json=json)
        except httpx.TimeoutException:
            raise BackendUnavailableError("The AgentOS service timed out.")
        except httpx.HTTPError:
            raise BackendUnavailableError("Couldn't reach the AgentOS service.")
        if resp.status_code == 204:
            return None
        if resp.is_success:
            try:
                return resp.json()
            except ValueError:
                raise BackendError("The AgentOS service returned an invalid response.", status_code=resp.status_code)
        self._raise_for(resp, method, path)

    @staticmethod
    def _raise_for(resp: httpx.Response, method: str, path: str) -> None:
        code, message, details = None, None, None
        try:
            err = resp.json().get("error") or {}
            code, message, details = err.get("code"), err.get("message"), err.get("details")
        except (ValueError, AttributeError):
            pass
        status = resp.status_code
        # Log the route and status only: bodies can contain user data and headers carry the token.
        logger.info("Backend call failed", extra={"method": method, "path": path, "status": status, "code": code})
        if status in (401, 403):
            raise BackendAuthError(message or "Not authorized.", status_code=status, code=code)
        if status == 404:
            raise BackendNotFoundError(message or "Not found.", status_code=status, code=code)
        if status in (400, 409, 422):
            raise BackendValidationError(
                message or "The request was rejected.", status_code=status, code=code, details=details
            )
        if status == 429:
            raise BackendRateLimitError("The AgentOS service is rate limiting requests.", status_code=status)
        if status >= 500:
            raise BackendUnavailableError("The AgentOS service had an error.", status_code=status)
        raise BackendError(message or "Unexpected response from the AgentOS service.", status_code=status, code=code)

    async def _one(self, model: type[M], method: str, path: str, **kw) -> M:
        return model.model_validate(await self._request(method, path, **kw))

    async def _many(self, model: type[M], path: str, **kw) -> list[M]:
        return [model.model_validate(x) for x in await self._request("GET", path, **kw)]

    async def _page(self, model: type[M], path: str, **kw) -> s.Page[M]:
        data = await self._request("GET", path, **kw)
        return s.Page[model].model_validate(data)  # type: ignore[valid-type]

    # --- identity & context ------------------------------------------------------------------------

    async def get_me(self) -> s.UserProfile:
        return await self._one(s.UserProfile, "GET", "/users/me")

    async def get_preferences(self) -> s.Preferences:
        return await self._one(s.Preferences, "GET", "/users/me/preferences")

    async def update_preferences(self, patch: dict[str, Any]) -> s.Preferences:
        return await self._one(s.Preferences, "PATCH", "/users/me/preferences", json=patch)

    async def get_conversation_messages(self, conversation_id: str) -> list[s.ConversationMessage]:
        return await self._many(s.ConversationMessage, f"/conversations/{conversation_id}/messages")

    # --- tasks -------------------------------------------------------------------------------------

    async def list_tasks(self, **filters: Any) -> s.Page[s.Task]:
        return await self._page(s.Task, "/tasks", params=filters)

    async def get_task(self, task_id: str) -> s.Task:
        return await self._one(s.Task, "GET", f"/tasks/{task_id}")

    async def create_task(self, body: dict[str, Any]) -> s.Task:
        return await self._one(s.Task, "POST", "/tasks", json=body)

    async def update_task(self, task_id: str, patch: dict[str, Any]) -> s.Task:
        return await self._one(s.Task, "PATCH", f"/tasks/{task_id}", json=patch)

    async def delete_task(self, task_id: str) -> None:
        await self._request("DELETE", f"/tasks/{task_id}")

    # --- subjects & study --------------------------------------------------------------------------

    async def list_subjects(self) -> list[s.Subject]:
        return await self._many(s.Subject, "/subjects")

    async def list_study_plans(self, status: str | None = None) -> list[s.StudyPlan]:
        return await self._many(s.StudyPlan, "/study-plans", params={"status": status})

    async def get_study_plan(self, plan_id: str) -> s.StudyPlan:
        return await self._one(s.StudyPlan, "GET", f"/study-plans/{plan_id}")

    async def generate_study_plan(self, spec: dict[str, Any]) -> s.StudyPlanDraft:
        return await self._one(s.StudyPlanDraft, "POST", "/study-plans/generate", json=spec)

    async def create_study_plan(self, body: dict[str, Any]) -> s.StudyPlan:
        return await self._one(s.StudyPlan, "POST", "/study-plans", json=body)

    async def update_study_plan(self, plan_id: str, patch: dict[str, Any]) -> s.StudyPlan:
        return await self._one(s.StudyPlan, "PATCH", f"/study-plans/{plan_id}", json=patch)

    async def list_study_sessions(self, **filters: Any) -> list[s.StudySession]:
        return await self._many(s.StudySession, "/study-sessions", params=filters)

    async def create_study_session(self, body: dict[str, Any]) -> s.StudySession:
        return await self._one(s.StudySession, "POST", "/study-sessions", json=body)

    async def update_study_session(self, session_id: str, patch: dict[str, Any]) -> s.StudySession:
        return await self._one(s.StudySession, "PATCH", f"/study-sessions/{session_id}", json=patch)

    # --- events ------------------------------------------------------------------------------------

    async def list_events(self, **filters: Any) -> list[s.Event]:
        return await self._many(s.Event, "/events", params=filters)

    async def create_event(self, body: dict[str, Any]) -> s.Event:
        return await self._one(s.Event, "POST", "/events", json=body)

    async def update_event(self, event_id: str, patch: dict[str, Any]) -> s.Event:
        return await self._one(s.Event, "PATCH", f"/events/{event_id}", json=patch)

    async def delete_event(self, event_id: str) -> None:
        await self._request("DELETE", f"/events/{event_id}")

    # --- reminders ---------------------------------------------------------------------------------

    async def list_reminders(self, status: list[str] | None = None) -> list[s.Reminder]:
        return await self._many(s.Reminder, "/reminders", params={"status": status})

    async def create_reminder(self, body: dict[str, Any]) -> s.Reminder:
        return await self._one(s.Reminder, "POST", "/reminders", json=body)

    async def update_reminder(self, reminder_id: str, patch: dict[str, Any]) -> s.Reminder:
        return await self._one(s.Reminder, "PATCH", f"/reminders/{reminder_id}", json=patch)

    async def complete_reminder(self, reminder_id: str) -> s.Reminder:
        return await self._one(s.Reminder, "POST", f"/reminders/{reminder_id}/complete")

    async def snooze_reminder(self, reminder_id: str, minutes: int) -> s.Reminder:
        return await self._one(s.Reminder, "POST", f"/reminders/{reminder_id}/snooze", json={"minutes": minutes})

    # --- finance -----------------------------------------------------------------------------------

    async def list_bills(self, **filters: Any) -> list[s.Bill]:
        return await self._many(s.Bill, "/bills", params=filters)

    async def create_bill(self, body: dict[str, Any]) -> s.Bill:
        return await self._one(s.Bill, "POST", "/bills", json=body)

    async def update_bill(self, bill_id: str, patch: dict[str, Any]) -> s.Bill:
        return await self._one(s.Bill, "PATCH", f"/bills/{bill_id}", json=patch)

    async def mark_bill_paid(self, bill_id: str, body: dict[str, Any]) -> s.BillPayment:
        return await self._one(s.BillPayment, "POST", f"/bills/{bill_id}/pay", json=body)

    async def list_payments(self, **filters: Any) -> s.Page[s.Payment]:
        return await self._page(s.Payment, "/payments", params=filters)

    async def list_payment_plans(self, status: str | None = None) -> list[s.PaymentPlan]:
        return await self._many(s.PaymentPlan, "/payment-plans", params={"status": status})

    async def create_payment_plan(self, body: dict[str, Any]) -> s.PaymentPlan:
        return await self._one(s.PaymentPlan, "POST", "/payment-plans", json=body)

    async def list_expenses(self, **filters: Any) -> s.Page[s.Expense]:
        return await self._page(s.Expense, "/expenses", params=filters)

    async def expense_summary(self, month: str | None = None) -> s.ExpenseSummary:
        return await self._one(s.ExpenseSummary, "GET", "/expenses/summary", params={"month": month})

    async def create_expense(self, body: dict[str, Any]) -> s.Expense:
        return await self._one(s.Expense, "POST", "/expenses", json=body)

    async def list_subscriptions(self, status: str | None = None) -> list[s.Subscription]:
        return await self._many(s.Subscription, "/subscriptions", params={"status": status})

    async def create_subscription(self, body: dict[str, Any]) -> s.Subscription:
        return await self._one(s.Subscription, "POST", "/subscriptions", json=body)

    async def update_subscription(self, sub_id: str, patch: dict[str, Any]) -> s.Subscription:
        return await self._one(s.Subscription, "PATCH", f"/subscriptions/{sub_id}", json=patch)

    async def list_budgets(self, month: str | None = None) -> list[s.Budget]:
        return await self._many(s.Budget, "/budgets", params={"month": month})

    async def create_budget(self, body: dict[str, Any]) -> s.Budget:
        return await self._one(s.Budget, "POST", "/budgets", json=body)

    async def update_budget(self, budget_id: str, patch: dict[str, Any]) -> s.Budget:
        return await self._one(s.Budget, "PATCH", f"/budgets/{budget_id}", json=patch)

    async def create_subject(self, body: dict[str, Any]) -> s.Subject:
        return await self._one(s.Subject, "POST", "/subjects", json=body)

    # --- goals -------------------------------------------------------------------------------------

    async def list_goals(self, **filters: Any) -> list[s.Goal]:
        return await self._many(s.Goal, "/goals", params=filters)

    async def create_goal(self, body: dict[str, Any]) -> s.Goal:
        return await self._one(s.Goal, "POST", "/goals", json=body)

    async def update_goal(self, goal_id: str, patch: dict[str, Any]) -> s.Goal:
        return await self._one(s.Goal, "PATCH", f"/goals/{goal_id}", json=patch)

    # --- documents ---------------------------------------------------------------------------------

    async def list_documents(self, **filters: Any) -> s.Page[s.Document]:
        return await self._page(s.Document, "/documents", params=filters)

    async def get_document(self, doc_id: str) -> s.Document:
        return await self._one(s.Document, "GET", f"/documents/{doc_id}")

    async def search_documents(self, query: str, *, top_k: int | None = None,
                               document_ids: list[str] | None = None) -> s.DocumentSearch:
        """Semantic search over the signed-in user's documents (the backend scopes it to them)."""
        body: dict[str, Any] = {"query": query}
        if top_k:
            body["topK"] = top_k
        if document_ids:
            body["documentIds"] = document_ids
        return await self._one(s.DocumentSearch, "POST", "/documents/search", json=body)

    # --- health ------------------------------------------------------------------------------------

    @staticmethod
    async def ping(base_url: str, *, timeout: float = 3.0, transport: httpx.AsyncBaseTransport | None = None) -> bool:
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=transport) as http:
                resp = await http.get(f"{base_url.rstrip('/')}/health")
                return resp.is_success
        except httpx.HTTPError:
            return False
