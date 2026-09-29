import io
from datetime import timedelta

from pypdf import PdfWriter

from app.core.timeutils import utcnow
from app.jobs import scheduler
from app.models import Approval, Reminder, User
from app.models.enums import ApprovalStatus


def _pdf(pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_upload_download_delete_pdf(client, auth, other_auth):
    resp = client.post(
        "/api/v1/documents",
        headers=auth,
        files={"file": ("notes.pdf", _pdf(3), "application/pdf")},
        data={"category": "Lecture notes"},
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    assert doc["status"] == "ready" and doc["pageCount"] == 3 and doc["category"] == "Lecture notes"

    download = client.get(doc["downloadUrl"], headers=auth)
    assert download.status_code == 200 and download.content.startswith(b"%PDF")
    assert client.get(doc["downloadUrl"], headers=other_auth).status_code == 404

    assert client.delete(f"/api/v1/documents/{doc['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=auth).status_code == 404


def test_upload_rejects_bad_files(client, auth):
    exe = client.post("/api/v1/documents", headers=auth, files={"file": ("run.exe", b"MZ...", "application/octet-stream")})
    assert exe.status_code == 415
    fake_pdf = client.post("/api/v1/documents", headers=auth, files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    assert fake_pdf.status_code == 415
    empty = client.post("/api/v1/documents", headers=auth, files={"file": ("x.txt", b"", "text/plain")})
    assert empty.status_code == 422


def test_scheduler_delivers_due_reminder_once(client, auth, db):
    client.post(
        "/api/v1/reminders",
        headers=auth,
        json={"title": "Stand up", "scheduledAt": (utcnow() - timedelta(minutes=1)).isoformat()},
    )
    assert scheduler.run_once()["reminders"] == 1
    assert scheduler.run_once()["reminders"] == 0  # idempotent
    notes = client.get("/api/v1/notifications", headers=auth).json()
    assert notes["total"] == 1 and notes["items"][0]["type"] == "reminder"

    note_id = notes["items"][0]["id"]
    assert client.post(f"/api/v1/notifications/{note_id}/read", headers=auth).json()["readAt"] is not None
    assert client.get("/api/v1/notifications/unread-count", headers=auth).json()["unread"] == 0


def test_scheduler_respects_muted_reminders(client, auth, db):
    client.patch("/api/v1/users/me/preferences", headers=auth, json={"notificationPreferences": {"reminders": False}})
    client.post(
        "/api/v1/reminders", headers=auth, json={"title": "Muted", "scheduledAt": (utcnow() - timedelta(minutes=1)).isoformat()}
    )
    assert scheduler.run_once()["reminders"] == 0
    reminder = db.query(Reminder).one()
    assert reminder.last_notified_at is not None


def test_scheduler_flags_overdue_bills_and_expires_approvals(client, auth, db):
    client.post("/api/v1/bills", headers=auth, json={"title": "Hostel", "amount": 5000, "dueDate": "2026-12-01"})
    # Move the bill into the past behind the API's back, as the passage of time would.
    from app.models import Bill

    bill = db.query(Bill).one()
    bill.due_date = bill.due_date.replace(year=2020)
    user = db.query(User).one()
    db.add(Approval(user_id=user.id, action="create_task", action_label="Create task", title="Old", payload={},
                    status=ApprovalStatus.PENDING, expires_at=utcnow() - timedelta(hours=1)))
    db.commit()

    results = scheduler.run_once()
    assert results["bills"] == 1 and results["approvals_expired"] == 1
    assert client.get("/api/v1/bills", headers=auth).json()[0]["status"] == "overdue"
    assert client.get("/api/v1/approvals", headers=auth, params={"status": "expired"}).json()["total"] == 1
