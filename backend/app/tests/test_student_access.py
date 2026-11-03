from app.models import Role, User


def test_student_scoped_even_with_group_access(client, db, world, auth, alerts):
    headers = auth["viewer"]
    assert client.get("/api/v1/auth/me", headers=headers).json()["student_id"] == "HS001"
    assert client.get("/api/v1/auth/me", headers=headers).json()["group_ids"] == []
    for path in ("groups", "learners", "programs", f"reports/group/{world['group_a'].id}", "reports/program/P1"):
        assert client.get(f"/api/v1/{path}", headers=headers).status_code == 403
    for sid in ("HS002", "HS003"):
        assert client.get(f"/api/v1/reports/learner/{sid}", headers=headers).status_code == 403
        assert client.get("/api/v1/metrics/results", params={"learner_id": sid}, headers=headers).status_code == 403
    items = client.get("/api/v1/metrics/results", headers=headers).json()["items"]
    assert items and all(r["learner_id"] == "HS001" for r in items)
    # API rà soát nội bộ (có ghi chú của giáo viên) chặn hẳn sinh viên; sinh viên dùng /me/alerts.
    for path in ("review/alerts", f"review/alerts/{alerts[0].id}", "support-cases", "followups"):
        assert client.get(f"/api/v1/{path}", headers=headers).status_code == 403
    own = client.get("/api/v1/me/alerts", headers=headers).json()["items"]
    assert own and all("review_note" not in a for a in own)


def test_student_binding_admin_only_and_immediate(client, db, world, auth):
    url = f"/api/v1/auth/users/{world['viewer'].id}/student-link"
    for role in ("viewer", "reviewer"):
        assert client.put(url, json={"student_id": "HS002"}, headers=auth[role]).status_code == 403
    assert client.put(url, json={"student_id": "MISSING"}, headers=auth["admin"]).status_code == 404
    assert client.put(url, json={"student_id": "HS003"}, headers=auth["admin"]).status_code == 200
    # Existing token must use new database binding, not old group or token claims.
    assert client.get("/api/v1/reports/learner/HS003", headers=auth["viewer"]).status_code == 200
    assert client.get("/api/v1/reports/learner/HS001", headers=auth["viewer"]).status_code == 403
    assert client.put(url, json={"student_id": None}, headers=auth["admin"]).status_code == 200
    assert client.get("/api/v1/reports/learner/HS003", headers=auth["viewer"]).status_code == 403
    assert client.get("/api/v1/me/alerts", headers=auth["viewer"]).status_code == 403  # chưa liên kết mã SV


def test_student_link_unique_and_staff_not_linked(client, db, world, auth):
    other = User(email="other@test.local", full_name="Other", hashed_password="-", role=Role.VIEWER)
    db.add(other)
    db.commit()
    url = f"/api/v1/auth/users/{other.id}/student-link"
    assert client.put(url, json={"student_id": "HS001"}, headers=auth["admin"]).status_code == 409
    url = f"/api/v1/auth/users/{world['reviewer'].id}/student-link"
    assert client.put(url, json={"student_id": "HS001"}, headers=auth["admin"]).status_code == 400


def test_legacy_users_migration_is_repeatable(engine):
    from sqlalchemy import text, inspect
    from app.db.session import init_db
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users DROP COLUMN student_id CASCADE"))
    init_db(engine)
    init_db(engine)
    assert "student_id" in {c["name"] for c in inspect(engine).get_columns("users")}
