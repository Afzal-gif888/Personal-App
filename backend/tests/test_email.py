"""Login OTP (EmailJS), reminder emails, password reset and email retries."""

import logging
import re
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.timeutils import utcnow
from app.jobs import scheduler
from app.models import LoginOtp, User
from app.services import auth_service
from tests.conftest import PASSWORD, SessionLocal, register, sign_in


def _signup(client, email):
    resp = client.post("/api/v1/auth/register", json={"name": "Student", "email": email, "password": PASSWORD})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login(client, email, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _verify(client, email, otp):
    return client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": otp})


def _resend(client, email):
    return client.post("/api/v1/auth/resend-otp", json={"email": email})


def _pending(email) -> LoginOtp | None:
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email)).one()
        return db.scalar(select(LoginOtp).where(LoginOtp.user_id == user.id))


def _age_pending(email, **fields):
    """Move the pending sign-in's clock (expiry / last send) into the past."""
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email)).one()
        row = db.scalar(select(LoginOtp).where(LoginOtp.user_id == user.id))
        for key, delta in fields.items():
            setattr(row, key, utcnow() - delta)
        db.commit()


def _wrong(otp: str) -> str:
    return f"{(int(otp) + 1) % 1_000_000:06d}"


# --- registration ---------------------------------------------------------------------------------


def test_registration_sends_no_email_and_no_session(client, emailjs):
    body = _signup(client, "new.student@example.com")
    assert emailjs.sent == []
    assert "accessToken" not in body and "token" not in body
    assert "emailVerified" not in body["user"]


# --- step 1: password -> OTP, never a token -------------------------------------------------------


def test_login_sends_otp_without_issuing_a_token(client, emailjs):
    _signup(client, "a@example.com")
    resp = _login(client, "A@Example.com")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True and body["requiresOtp"] is True and body["message"] == "OTP sent to your email."
    assert not {"accessToken", "refreshToken", "token"} & body.keys()
    [sent] = emailjs.sent
    params = sent["template_params"]
    assert sent["template_id"] == "template_otp" and sent["user_id"] == "public-test" and sent["accessToken"] == "private-test"
    assert params["to_email"] == "a@example.com" and params["name"] == "Student"
    otp = params["otp"]
    assert re.fullmatch(r"\d{6}", otp) and otp not in resp.text  # never returned by the API
    row = _pending("a@example.com")
    assert row is not None and row.otp_hash and otp not in row.otp_hash  # only a keyed hash is stored
    assert timedelta(minutes=4) < row.expires_at.replace(tzinfo=None) - utcnow().replace(tzinfo=None) <= timedelta(minutes=5)


def test_wrong_password_sends_nothing(client, emailjs):
    _signup(client, "b@example.com")
    wrong = _login(client, "b@example.com", "wrong-password")
    unknown = _login(client, "nobody@example.com", "wrong-password")
    assert wrong.status_code == unknown.status_code == 401 and wrong.json() == unknown.json()
    assert emailjs.sent == []


# --- step 2: the code -----------------------------------------------------------------------------


def test_correct_otp_issues_jwt_and_opens_agentos(client, emailjs):
    _signup(client, "c@example.com")
    _login(client, "c@example.com")
    resp = _verify(client, "c@example.com", emailjs.otps("c@example.com")[-1])
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True and body["message"] == "Login successful"
    assert body["token"] == body["accessToken"] and body["refreshToken"]
    headers = {"Authorization": f"Bearer {body['token']}"}
    assert client.post("/api/v1/tasks", headers=headers, json={"title": "Finish lab report"}).status_code == 201
    assert client.get("/api/v1/users/me", headers=headers).json()["email"] == "c@example.com"
    assert _pending("c@example.com") is None  # deleted after use


def test_incorrect_otp_is_rejected(client, emailjs):
    _signup(client, "d@example.com")
    _login(client, "d@example.com")
    resp = _verify(client, "d@example.com", _wrong(emailjs.otps("d@example.com")[-1]))
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "OTP_INVALID" and err["details"] == {"attemptsLeft": 4}
    assert "accessToken" not in resp.text


def test_malformed_otp_is_a_validation_error(client):
    for bad in ["12345", "1234567", "abcdef", ""]:
        assert _verify(client, "x@example.com", bad).status_code == 422


def test_expired_otp_is_rejected(client, emailjs):
    _signup(client, "e@example.com")
    _login(client, "e@example.com")
    otp = emailjs.otps("e@example.com")[-1]
    _age_pending("e@example.com", expires_at=timedelta(seconds=1))
    resp = _verify(client, "e@example.com", otp)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "OTP_EXPIRED"


def test_otp_cannot_be_reused(client, emailjs):
    _signup(client, "f@example.com")
    _login(client, "f@example.com")
    otp = emailjs.otps("f@example.com")[-1]
    assert _verify(client, "f@example.com", otp).status_code == 200
    again = _verify(client, "f@example.com", otp)
    assert again.status_code == 400 and again.json()["error"]["code"] == "OTP_INVALID"


def test_too_many_attempts_locks_the_code(client, emailjs):
    _signup(client, "g@example.com")
    _login(client, "g@example.com")
    otp = emailjs.otps("g@example.com")[-1]
    codes = [_verify(client, "g@example.com", _wrong(otp)).json()["error"]["code"] for _ in range(5)]
    assert codes == ["OTP_INVALID"] * 4 + ["OTP_TOO_MANY_ATTEMPTS"]
    locked = _verify(client, "g@example.com", otp)  # even the right code no longer works
    assert locked.status_code == 400 and locked.json()["error"]["code"] == "OTP_TOO_MANY_ATTEMPTS"
    _age_pending("g@example.com", sent_at=timedelta(minutes=1))
    assert sign_in(client, "g@example.com")["accessToken"]  # signing in again issues a fresh code


def test_otp_for_one_account_does_not_work_for_another(client, emailjs):
    _signup(client, "h1@example.com")
    _signup(client, "h2@example.com")
    _login(client, "h1@example.com")
    _login(client, "h2@example.com")
    resp = _verify(client, "h2@example.com", emailjs.otps("h1@example.com")[-1])
    assert resp.status_code == 400


# --- resend ---------------------------------------------------------------------------------------


def test_resend_sends_a_new_code_and_invalidates_the_old_one(client, emailjs):
    _signup(client, "i@example.com")
    _login(client, "i@example.com")
    old = emailjs.otps("i@example.com")[-1]
    _age_pending("i@example.com", sent_at=timedelta(seconds=31))
    resp = _resend(client, "i@example.com")
    assert resp.status_code == 200 and resp.json() == {"success": True, "message": "A new OTP has been sent."}
    new = emailjs.otps("i@example.com")[-1]
    assert len(emailjs.otps("i@example.com")) == 2 and new not in resp.text
    if new != old:  # 1-in-a-million chance the new random code equals the old one
        stale = _verify(client, "i@example.com", old)
        assert stale.status_code == 400 and stale.json()["error"]["code"] == "OTP_INVALID"
    assert _verify(client, "i@example.com", new).status_code == 200


def test_resend_cooldown_and_send_limit(client, emailjs):
    _signup(client, "j@example.com")
    _login(client, "j@example.com")
    soon = _resend(client, "j@example.com")
    assert soon.status_code == 429 and soon.json()["error"]["code"] == "OTP_RESEND_COOLDOWN"
    assert 0 < soon.json()["error"]["details"]["retryAfter"] <= 30
    again = _login(client, "j@example.com")  # logging in again doesn't bypass the cooldown
    assert again.status_code == 429
    for _ in range(auth_service.OTP_MAX_SENDS - 1):
        _age_pending("j@example.com", sent_at=timedelta(seconds=31))
        assert _resend(client, "j@example.com").status_code == 200
    _age_pending("j@example.com", sent_at=timedelta(seconds=31))
    capped = _resend(client, "j@example.com")
    assert capped.status_code == 429 and capped.json()["error"]["code"] == "OTP_SEND_LIMIT"
    assert len(emailjs.otps("j@example.com")) == auth_service.OTP_MAX_SENDS


def test_resend_does_not_reveal_accounts_or_email_strangers(client, emailjs):
    _signup(client, "k@example.com")  # registered, but no sign-in in progress
    no_login = _resend(client, "k@example.com")
    unknown = _resend(client, "nobody@example.com")
    assert no_login.status_code == unknown.status_code == 200 and no_login.json() == unknown.json()
    assert emailjs.sent == []


# --- the server is the source of truth ------------------------------------------------------------


def test_protected_api_is_closed_before_the_otp(client, emailjs):
    _signup(client, "l@example.com")
    step1 = _login(client, "l@example.com")
    assert step1.status_code == 200
    for method, path in [("GET", "/api/v1/users/me"), ("GET", "/api/v1/tasks"), ("POST", "/api/v1/tasks"),
                         ("GET", "/api/v1/conversations"), ("GET", "/api/v1/dashboard"), ("GET", "/api/v1/notifications")]:
        assert client.request(method, path, json={"title": "x"} if method == "POST" else None).status_code == 401
        forged = client.request(method, path, headers={"Authorization": "Bearer requires-otp"})
        assert forged.status_code == 401, (method, path)


def test_login_and_resend_are_rate_limited(client, emailjs, monkeypatch):
    from app.core import rate_limit as rl

    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    monkeypatch.setattr(get_settings(), "rate_limit_auth_per_minute", 3)
    rl.backend.reset()
    statuses = [_login(client, "nobody@example.com", "x").status_code for _ in range(4)]
    assert statuses[:3] == [401, 401, 401] and statuses[3] == 429
    assert _resend(client, "nobody@example.com").status_code == 429  # same per-IP auth budget
    rl.backend.reset()


def test_email_failure_issues_no_code_and_no_token(client, emailjs):
    _signup(client, "m@example.com")
    emailjs.status = 400
    resp = _login(client, "m@example.com")
    assert resp.status_code == 503 and resp.json()["error"]["code"] == "EMAIL_DELIVERY_FAILED"
    assert "accessToken" not in resp.text and _pending("m@example.com") is None


def test_otp_values_never_reach_the_logs(client, emailjs, caplog):
    caplog.set_level(logging.DEBUG)
    _signup(client, "n@example.com")
    _login(client, "n@example.com")
    otp = emailjs.otps("n@example.com")[-1]
    _verify(client, "n@example.com", _wrong(otp))
    emailjs.status = 400
    _age_pending("n@example.com", sent_at=timedelta(seconds=31))
    _resend(client, "n@example.com")  # failed send is logged
    logged = "\n".join(r.getMessage() + str(r.__dict__) for r in caplog.records)
    assert otp not in logged and "private-test" not in logged


# --- reminder emails ------------------------------------------------------------------------------


def _due_reminder(client, headers, title="Pay electricity bill"):
    resp = client.post("/api/v1/reminders", headers=headers,
                       json={"title": title, "scheduledAt": (utcnow() - timedelta(minutes=1)).isoformat()})
    assert resp.status_code == 201, resp.text


def _student(client, email):
    return {"Authorization": f"Bearer {register(client, email)['accessToken']}"}


def test_each_student_gets_their_own_reminders(client, emailjs):
    alice, bob = _student(client, "alice@example.com"), _student(client, "bob@example.com")
    _due_reminder(client, alice, "Alice: submit lab report")
    _due_reminder(client, bob, "Bob: pay hostel fee")
    assert scheduler.run_once()["reminders"] == 2
    assert {n["to_email"]: n["subject"] for n in emailjs.notifications()} == {
        "alice@example.com": "It's Personal: Alice: submit lab report", "bob@example.com": "It's Personal: Bob: pay hostel fee"}
    assert scheduler.run_once()["reminders"] == 0 and len(emailjs.notifications()) == 2  # never emailed twice


def test_students_can_turn_email_off(client, emailjs):
    auth = _student(client, "off@example.com")
    prefs = client.get("/api/v1/users/me/preferences", headers=auth).json()["notificationPreferences"]
    assert prefs["emailNotifications"] is True  # on by default
    client.patch("/api/v1/users/me/preferences", headers=auth, json={"notificationPreferences": {**prefs, "emailNotifications": False}})
    _due_reminder(client, auth)
    assert scheduler.run_once()["reminders"] == 1 and emailjs.notifications() == []  # in-app only


def test_failed_email_is_retried_then_given_up(client, emailjs):
    auth = _student(client, "retry@example.com")
    emailjs.status = 500
    _due_reminder(client, auth)
    scheduler.run_once()
    assert client.get("/api/v1/notifications", headers=auth).json()["items"][0]["metadata"]["email"]["status"] == "failed"
    emailjs.status = 200
    before = len(emailjs.notifications())
    assert scheduler.run_once()["emails_retried"] == 1 and len(emailjs.notifications()) == before + 1
    assert scheduler.run_once()["emails_retried"] == 0


def test_retries_stop_after_three_attempts(client, emailjs):
    auth = _student(client, "giveup@example.com")
    emailjs.status = 500
    _due_reminder(client, auth)
    for _ in range(4):
        scheduler.run_once()
    email = client.get("/api/v1/notifications", headers=auth).json()["items"][0]["metadata"]["email"]
    assert email["status"] == "failed" and email["attempts"] == 3


def test_unconfigured_email_is_recorded_not_raised(client, emailjs, monkeypatch):
    auth = _student(client, "unconf@example.com")
    monkeypatch.setattr(get_settings(), "emailjs_notification_template_id", "")
    _due_reminder(client, auth)
    assert scheduler.run_once()["reminders"] == 1
    email = client.get("/api/v1/notifications", headers=auth).json()["items"][0]["metadata"]["email"]
    assert email["status"] == "skipped" and email["reason"] == "email_not_configured"


# --- password reset -------------------------------------------------------------------------------


def _reset_token(emailjs):
    [msg] = [n for n in emailjs.notifications() if n["subject"] == "Reset your It's Personal password"][-1:]
    match = re.search(r"/reset-password\?token=(\S+)", msg["message"])
    assert match
    return match.group(1)


def test_password_reset_by_email(client, emailjs):
    register(client, "forgetful@example.com")
    assert client.post("/api/v1/auth/forgot-password", json={"email": "Forgetful@Example.com"}).status_code == 202
    token = _reset_token(emailjs)
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "newPassword": "brand-new-pass-1"}).status_code == 200
    assert _login(client, "forgetful@example.com").status_code == 401
    assert sign_in(client, "forgetful@example.com", "brand-new-pass-1")["accessToken"]
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "newPassword": "another-pass-2"}).status_code == 401


def test_forgot_password_does_not_reveal_accounts(client, emailjs):
    register(client, "exists@example.com")
    known = client.post("/api/v1/auth/forgot-password", json={"email": "exists@example.com"})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert len(emailjs.notifications()) == 1


def test_reset_signs_out_other_sessions(client, emailjs):
    tokens = register(client, "session@example.com")
    client.post("/api/v1/auth/forgot-password", json={"email": "session@example.com"})
    client.post("/api/v1/auth/reset-password", json={"token": _reset_token(emailjs), "newPassword": "brand-new-pass-1"})
    assert client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]}).status_code == 401


def test_access_log_lines_have_tokens_redacted():
    """uvicorn logs the request line; a reset link opened against the API would otherwise leak its token."""
    from app.core.logging import RedactingFilter

    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d', (
        "127.0.0.1:5000", "GET", "/reset-password?token=SeCrEtToKeN123456789&x=1", "1.1", 200), None)
    RedactingFilter().filter(record)
    line = record.getMessage()
    assert "SeCrEtToKeN" not in line and "token=[REDACTED]&x=1" in line
    assert any(isinstance(f, RedactingFilter) for f in logging.getLogger("uvicorn.access").filters)


@pytest.mark.parametrize("n", range(3))
def test_otps_are_six_digits_and_vary(n):
    from app.core.security import generate_otp

    codes = {generate_otp() for _ in range(50)}
    assert all(re.fullmatch(r"\d{6}", c) for c in codes) and len(codes) > 40


def test_reminder_email_shows_title_type_time_and_notes(client, emailjs):
    auth = _student(client, "details@example.com")
    resp = client.post("/api/v1/reminders", headers=auth, json={
        "title": "Pay electricity bill", "category": "financial", "description": "Use the UPI app",
        "scheduledAt": (utcnow() - timedelta(minutes=1)).isoformat()})
    assert resp.status_code == 201, resp.text
    scheduler.run_once()
    [email] = emailjs.notifications()
    lines = email["message"].splitlines()
    assert lines[:4] == ["Reminder: Pay electricity bill", "Type: Payment / financial", lines[2], "Notes: Use the UPI app"]
    assert lines[2].startswith("When: ")
    assert email["title"] == email["reminder"] == "Pay electricity bill" and email["type"] == "Payment / financial"
