from datetime import date, timedelta


def test_task_crud_filters_and_isolation(client, auth, other_auth):
    today = date.today()
    created = client.post(
        "/api/v1/tasks",
        headers=auth,
        json={"title": "ML assignment", "subject": "Machine Learning", "priority": "high", "dueDate": today.isoformat(), "dueTime": "17:00"},
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["subject"] == "Machine Learning" and task["dueTime"] == "17:00"
    client.post("/api/v1/tasks", headers=auth, json={"title": "Read chapter 3", "subject": "machine learning"})

    # Subject names are matched case-insensitively instead of duplicated.
    assert len(client.get("/api/v1/subjects", headers=auth).json()) == 1

    page = client.get("/api/v1/tasks", headers=auth, params={"priority": "high"}).json()
    assert page["total"] == 1 and page["items"][0]["id"] == task["id"]

    done = client.patch(f"/api/v1/tasks/{task['id']}", headers=auth, json={"status": "completed"}).json()
    assert done["completedAt"] is not None
    reopened = client.patch(f"/api/v1/tasks/{task['id']}", headers=auth, json={"status": "pending"}).json()
    assert reopened["completedAt"] is None

    assert client.patch(f"/api/v1/tasks/{task['id']}", headers=auth, json={"title": None}).status_code == 422
    # Another user can neither see nor touch it.
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=other_auth).status_code == 404
    assert client.delete(f"/api/v1/tasks/{task['id']}", headers=other_auth).status_code == 404
    assert client.get("/api/v1/tasks", headers=other_auth).json()["total"] == 0

    assert client.delete(f"/api/v1/tasks/{task['id']}", headers=auth).status_code == 204


def test_events_are_stored_in_utc_and_returned_in_user_timezone(client, auth):
    # The user is in Asia/Kolkata (UTC+05:30).
    resp = client.post(
        "/api/v1/events",
        headers=auth,
        json={"title": "DBMS lecture", "eventType": "class", "date": "2026-10-05", "startTime": "10:00", "endTime": "11:30"},
    )
    assert resp.status_code == 201, resp.text
    ev = resp.json()
    assert ev["startAt"].startswith("2026-10-05T10:00:00+05:30")
    assert ev["startTime"] == "10:00" and ev["endTime"] == "11:30"

    moved = client.patch(f"/api/v1/events/{ev['id']}", headers=auth, json={"date": "2026-10-06"}).json()
    assert moved["date"] == "2026-10-06" and moved["endTime"] == "11:30"  # duration kept

    listed = client.get("/api/v1/events", headers=auth, params={"start": "2026-10-06", "end": "2026-10-06"}).json()
    assert [e["id"] for e in listed] == [ev["id"]]

    bad = client.post(
        "/api/v1/events", headers=auth, json={"title": "x", "date": "2026-10-05", "startTime": "10:00", "endTime": "09:00"}
    )
    assert bad.status_code == 422


def test_reminder_complete_repeat_and_snooze(client, auth):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    one_off = client.post(
        "/api/v1/reminders", headers=auth, json={"title": "Submit form", "date": yesterday, "time": "09:00"}
    ).json()
    weekly = client.post(
        "/api/v1/reminders",
        headers=auth,
        json={"title": "Laundry", "date": yesterday, "time": "09:00", "repeatRule": "weekly"},
    ).json()

    done = client.post(f"/api/v1/reminders/{one_off['id']}/complete", headers=auth).json()
    assert done["status"] == "completed"

    rolled = client.post(f"/api/v1/reminders/{weekly['id']}/complete", headers=auth).json()
    assert rolled["status"] == "pending"
    assert rolled["date"] == (date.fromisoformat(yesterday) + timedelta(days=7)).isoformat()
    assert rolled["time"] == "09:00"

    snoozed = client.post(f"/api/v1/reminders/{weekly['id']}/snooze", headers=auth, json={"minutes": 15}).json()
    assert snoozed["status"] == "snoozed"


def test_study_plan_generation_avoids_busy_time(client, auth):
    start = date.today() + timedelta(days=3)
    client.patch("/api/v1/users/me/preferences", headers=auth, json={"preferredStudyStart": "18:00", "preferredStudyEnd": "21:00"})
    client.post(
        "/api/v1/events",
        headers=auth,
        json={"title": "Club meeting", "date": start.isoformat(), "startTime": "18:00", "endTime": "19:00"},
    )
    draft = client.post(
        "/api/v1/study-plans/generate",
        headers=auth,
        json={"subject": "Operating Systems", "startDate": start.isoformat(), "days": 2, "minutesPerDay": 90},
    )
    assert draft.status_code == 200, draft.text
    sessions = draft.json()["sessions"]
    first_day = [s for s in sessions if s["date"] == start.isoformat()]
    assert first_day and all(s["startTime"] >= "19:00" for s in first_day)

    saved = client.post("/api/v1/study-plans", headers=auth, json=draft.json())
    assert saved.status_code == 201, saved.text
    assert len(saved.json()["sessions"]) == len(sessions)
    assert len(client.get("/api/v1/study-sessions", headers=auth).json()) == len(sessions)


def test_goal_progress(client, auth):
    goal = client.post(
        "/api/v1/goals", headers=auth, json={"title": "Save", "category": "financial", "targetValue": 20000, "currentValue": 8000}
    ).json()
    assert goal["progress"] == 40 and goal["targetValue"] == 20000.0
    manual = client.post("/api/v1/goals", headers=auth, json={"title": "Read books", "manualProgress": 60}).json()
    assert manual["progress"] == 60
    assert client.post("/api/v1/goals", headers=auth, json={"title": "x", "manualProgress": 150}).status_code == 422
