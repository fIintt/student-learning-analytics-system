from app.tests.conftest import add_term, login


def test_create_and_change_password(client, world, auth):
    body = {"email": "new@student.test", "student_id": "HS002", "password": "Temporary123"}
    assert client.post("/api/v1/admin/student-accounts", json=body, headers=auth["viewer"]).status_code == 403
    created = client.post("/api/v1/admin/student-accounts", json=body, headers=auth["admin"])
    assert created.status_code == 201, created.text
    assert created.json()["must_change_password"]
    assert "hashed_password" not in created.json()
    assert client.post("/api/v1/admin/student-accounts", json=body, headers=auth["admin"]).status_code == 409
    headers = login(client, body["email"], body["password"])
    assert client.get("/api/v1/me/student-profile", headers=headers).status_code == 403
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    changed = client.post("/api/v1/auth/change-password", json={"current_password": body["password"], "password": "NewPassword123"}, headers=headers)
    assert changed.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    headers = login(client, body["email"], "NewPassword123")
    assert client.get("/api/v1/me/student-profile", headers=headers).json()["student_id"] == "HS002"
    uid = created.json()["id"]
    assert client.patch(f"/api/v1/admin/student-accounts/{uid}", json={"is_active": False}, headers=auth["admin"]).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    client.patch(f"/api/v1/admin/student-accounts/{uid}", json={"is_active": True}, headers=auth["admin"])
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post(f"/api/v1/admin/student-accounts/{uid}/reset-password", json={"password": "ResetPassword123"}, headers=auth["admin"]).status_code == 200
    headers = login(client, body["email"], "ResetPassword123")
    assert client.get("/api/v1/auth/me", headers=headers).json()["must_change_password"]


def test_student_statistics_and_isolation(client, db, world, auth):
    add_term(db, "HS001", "2024-2025", 1, registered=20, failed=5, semester_gpa=2.0, cumulative_gpa=2.2)
    add_term(db, "HS001", "2025-2026", 1, registered=0, failed=0, semester_gpa=3.0, cumulative_gpa=2.7)
    add_term(db, "HS002", semester_gpa=4.0)
    headers = auth["viewer"]
    summary = client.get("/api/v1/me/academic-summary", headers=headers).json()
    assert summary["term_count"] == 2
    assert summary["latest"]["gpa_change"] == 1.0
    assert summary["latest"]["cumulative_gpa"] == 2.7
    assert summary["latest"]["passed_percent"] is None
    assert summary["trend"][0]["passed_percent"] == 75
    assert summary["trend"][0]["gpa_change"] is None
    assert summary["highest_semester_gpa"] == 3.0
    rows = client.get("/api/v1/me/academic-performance?academic_year=2024-2025&student_id=HS002", headers=headers).json()
    assert rows["total"] == 1 and rows["items"][0]["semester_gpa"] == 2.0
    assert client.get("/api/v1/me/academic-performance?semester=9", headers=headers).status_code == 400


def test_empty_and_unlinked(client, db, world, auth):
    result = client.get("/api/v1/me/academic-summary", headers=auth["viewer"]).json()
    assert result["trend"] == [] and result["latest"] is None
    world["viewer"].student_id = None
    db.commit()
    assert client.get("/api/v1/me/academic-summary", headers=auth["viewer"]).status_code == 403


def test_private_alerts(client, world, auth, alerts):
    data = client.get("/api/v1/me/alerts", headers=auth["viewer"]).json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == alerts[0].id
    assert "review_note" not in data["items"][0]
    assert client.get(f"/api/v1/me/alerts/{alerts[1].id}", headers=auth["viewer"]).status_code == 404


def test_alert_shows_advisor_contact_line(client, world, auth, alerts):
    url = f"/api/v1/me/alerts/{alerts[0].id}"
    # Chưa có case: chưa hiện dòng liên hệ.
    item = client.get(url, headers=auth["viewer"]).json()
    assert (item["support_status"], item["advisor_name"], item["support_message"]) == (None, None, None)

    body = {"note": "Đã kiểm tra", "reason": "Lý do nội bộ không cho sinh viên xem"}
    confirm = client.post(f"/api/v1/review/alerts/{alerts[0].id}/confirm", json=body, headers=auth["reviewer"])
    case_id = confirm.json()["support_case"]["id"]
    item = client.get(url, headers=auth["viewer"]).json()
    assert item["support_status"] == "open"
    assert item["support_message"] == "Cố vấn học tập sẽ liên hệ với bạn."  # chưa giao người phụ trách

    client.patch(f"/api/v1/support-cases/{case_id}", json={"status": "in_progress", "assigned_to": world["reviewer"].id},
                 headers=auth["reviewer"])
    item = client.get("/api/v1/me/alerts", headers=auth["viewer"]).json()["items"][0]
    name = world["reviewer"].full_name
    assert (item["support_status"], item["advisor_name"]) == ("in_progress", name)
    assert item["support_message"] == f"Cố vấn học tập {name} sẽ liên hệ với bạn."
    assert "Lý do nội bộ" not in str(item)

    client.patch(f"/api/v1/support-cases/{case_id}", json={"status": "closed"}, headers=auth["reviewer"])
    item = client.get(url, headers=auth["viewer"]).json()
    assert (item["support_status"], item["support_message"]) == ("closed", "Trường hợp hỗ trợ của bạn đã kết thúc.")


def test_account_validation_and_upgrade(client, db, engine, world, auth):
    from sqlalchemy import text, inspect
    from app.db.session import init_db
    endpoint = "/api/v1/admin/student-accounts"
    for role in ("viewer", "reviewer"):
        assert client.get(endpoint, headers=auth[role]).status_code == 403
    body = {"email": "bad", "student_id": "HS002", "password": "Temporary123"}
    assert client.post(endpoint, json=body, headers=auth["admin"]).status_code == 400
    body.update(email="test@student.local", student_id="MISSING")
    assert client.post(endpoint, json=body, headers=auth["admin"]).status_code == 404
    body.update(student_id="HS001")
    assert client.post(endpoint, json=body, headers=auth["admin"]).status_code == 409
    db.rollback()
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users DROP COLUMN must_change_password, DROP COLUMN token_version"))
    init_db(engine)
    init_db(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("users")}
    assert {"must_change_password", "token_version"} <= columns
