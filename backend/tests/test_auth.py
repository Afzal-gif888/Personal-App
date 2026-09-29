from tests.conftest import PASSWORD, register, sign_in


def test_register_login_and_me(client):
    tokens = register(client)
    assert tokens["tokenType"] == "bearer" and tokens["refreshToken"]
    assert tokens["user"]["email"] == "student@example.com"

    again = sign_in(client, "STUDENT@example.com")
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {again['accessToken']}"})
    assert me.status_code == 200 and me.json()["name"] == "Test Student"


def test_duplicate_email_and_bad_password(client):
    register(client)
    dup = client.post(
        "/api/v1/auth/register", json={"name": "X", "email": "student@example.com", "password": PASSWORD}
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "EMAIL_TAKEN"

    bad = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "wrong-pass"})
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-pass"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()  # no account enumeration


def test_requires_auth_and_rejects_garbage_token(client):
    assert client.get("/api/v1/tasks").status_code == 401
    resp = client.get("/api/v1/tasks", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401 and resp.json()["error"]["code"] == "INVALID_TOKEN"


def test_refresh_rotation_and_reuse_detection(client):
    tokens = register(client)
    first = client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert first.status_code == 200
    rotated = first.json()["refreshToken"]
    assert rotated != tokens["refreshToken"]

    # Replaying the old token revokes the whole family, including the newly issued one.
    replay = client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert replay.status_code == 401 and replay.json()["error"]["code"] == "TOKEN_REVOKED"
    assert client.post("/api/v1/auth/refresh", json={"refreshToken": rotated}).status_code == 401


def test_logout_revokes_refresh_token(client):
    tokens = register(client)
    assert client.post("/api/v1/auth/logout", json={"refreshToken": tokens["refreshToken"]}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]}).status_code == 401


def test_preferences_and_password_change(client, auth):
    prefs = client.get("/api/v1/users/me/preferences", headers=auth).json()
    assert prefs["timezone"] == "Asia/Kolkata" and prefs["notificationPreferences"]["reminders"] is True

    resp = client.patch(
        "/api/v1/users/me/preferences",
        headers=auth,
        json={"preferredStudyStart": "17:00", "preferredStudyEnd": "21:30", "notificationPreferences": {"reminders": False}},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["preferredStudyStart"] == "17:00"
    assert resp.json()["notificationPreferences"]["reminders"] is False

    bad_tz = client.patch("/api/v1/users/me/preferences", headers=auth, json={"timezone": "Mars/Base"})
    assert bad_tz.status_code == 422

    wrong = client.post("/api/v1/users/me/password", headers=auth, json={"currentPassword": "nope", "newPassword": "N3wPassword!"})
    assert wrong.status_code == 401
    ok = client.post("/api/v1/users/me/password", headers=auth, json={"currentPassword": PASSWORD, "newPassword": "N3wPassword!"})
    assert ok.status_code == 204
    assert sign_in(client, "student@example.com", "N3wPassword!")["accessToken"]


def test_validation_error_envelope(client):
    resp = client.post("/api/v1/auth/register", json={"name": "", "email": "not-an-email", "password": "short"})
    assert resp.status_code == 422
    body = resp.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert {d["field"] for d in body["details"]} >= {"name", "email", "password"}


def test_security_headers(client, auth):
    headers = client.get("/api/v1/tasks", headers=auth).headers
    assert headers["x-frame-options"] == "DENY" and headers["x-content-type-options"] == "nosniff"
    assert headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert "content-security-policy" not in client.get("/docs").headers  # Swagger UI needs its scripts
