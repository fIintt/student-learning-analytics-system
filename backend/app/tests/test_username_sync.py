from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text, select
from sqlalchemy.orm import Session

from app.models import User, Role
from app.core.security import verify_password
from app.tests.conftest import _TEST_PASSWORD_HASH


@pytest.fixture()
def source_accounts(db, world):
    schema_dir = Path(__file__).resolve().parents[2] / "pipeline/sql/schemas"
    for term in ("staff", "accounts"):
        candidates = list(schema_dir.glob(f"*create_{term}.sql"))
        assert len(candidates) == 1
        db.execute(text(candidates[0].read_text(encoding="utf-8")))
    db.execute(text("INSERT INTO staff VALUES ('QT001','Admin source','source-admin@test.local','Office','administrator'), ('GV001','Teacher source','source-teacher@test.local','Office','lecturer')"))
    rows = [(str(uuid4()), "qt0001", "admin", None, "QT001"),
            (str(uuid4()), "gv0001", "reviewer", None, "GV001"),
            (str(uuid4()), "hs002", "viewer", "HS002", None)]
    for source_id, username, role, student, staff in rows:
        db.execute(text("INSERT INTO accounts (account_id,username,password_hash,role,student_id,staff_id) VALUES (:id,:name,:hash,:role,:student,:staff)"),
                   dict(id=source_id,name=username,hash=_TEST_PASSWORD_HASH,role=role,student=student,staff=staff))
    db.commit()
    return rows


def test_sync_and_username_login(client, db, world, auth, source_accounts):
    url = "/api/v1/admin/accounts/sync"
    assert client.post(url, headers=auth["viewer"]).status_code == 403
    assert client.post(url, headers=auth["reviewer"]).status_code == 403
    result = client.post(url, headers=auth["admin"])
    assert result.status_code == 200, result.text
    assert result.json()["created"] == 3
    assert "password_hash" not in result.text
    assert client.post(url, headers=auth["admin"]).json()["skipped"] == 3
    for source_id, username, role, student, staff in source_accounts:
        login = client.post("/api/v1/auth/login", json={"username": f" {username.upper()} ", "password": "Test@123"})
        assert login.status_code == 200, login.text
        assert login.json()["user"]["username"] == username
        assert login.json()["user"]["role"] == role
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        me = client.get("/api/v1/auth/me", headers=headers).json()
        assert me["student_id"] == student and me["group_ids"] == ([] if role != "admin" else [world["group_a"].id, world["group_b"].id])
        assert me["must_change_password"]
        assert client.get("/api/v1/me/student-profile", headers=headers).status_code == 403
    assert db.scalar(text("SELECT count(*) FROM accounts")) == 3


def test_sync_preserves_password_lock_groups(client, db, engine, world, auth, source_accounts):
    from app.services.account_sync_service import sync_accounts
    sync_accounts(db)
    user = db.scalar(select(User).where(User.username == "hs002"))
    original_id = user.id
    # Change password via the actual API, then ensure sync cannot restore CSV password.
    response = client.post("/api/v1/auth/login", json={"username": "hs002", "password": "Test@123"})
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert client.post("/api/v1/auth/change-password", headers=headers, json={"current_password":"Test@123", "password":"Changed123!"}).status_code == 200
    client.patch(f"/api/v1/admin/student-accounts/{user.id}", headers=auth["admin"], json={"is_active": False})
    user.groups = [world["group_b"]]
    db.commit()
    sync_accounts(db)
    db.expire_all()
    assert user.id == original_id and not user.is_active and not user.must_change_password
    assert verify_password("Changed123!", user.hashed_password)
    assert user.groups[0].id == world["group_b"].id
    assert db.scalar(text("SELECT password_hash FROM accounts WHERE username='hs002'")) == _TEST_PASSWORD_HASH


def test_sync_conflict_and_source_change(client, db, world, auth, source_accounts):
    # Existing unlinked account is never silently taken over by a source row.
    user = User(username="hs002", full_name="Existing", role=Role.VIEWER, hashed_password="-")
    db.add(user); db.commit()
    data = client.post("/api/v1/admin/accounts/sync", headers=auth["admin"]).json()
    assert data["created"] == 2 and data["conflicts"] == 1
    assert db.get(User, user.id).student_id is None
    db.execute(text("UPDATE accounts SET username='newteacher' WHERE username='gv0001'"));db.commit()
    data = client.post("/api/v1/admin/accounts/sync", headers=auth["admin"]).json()
    assert any(r["reason"] == "source_identity_changed" for r in data["items"])
    assert db.scalar(select(User).where(User.username == "gv0001")) is not None


def test_missing_source(client, db, world, auth):
    assert client.post("/api/v1/admin/accounts/sync", headers=auth["admin"]).status_code == 503


def test_create_student_with_username_no_email(client, world, auth):
    response = client.post("/api/v1/admin/student-accounts", headers=auth["admin"], json={"username":"  SV002  ","student_id":"HS002","password":"Temporary123!"})
    assert response.status_code == 201, response.text
    assert response.json()["username"] == "sv002" and response.json()["email"] is None
    assert client.post("/api/v1/auth/login", json={"username":"sv002","password":"Temporary123!"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"username":"sv002","password":"wrong"}).status_code == 401


def test_legacy_username_migration(engine, db, world):
    from app.db.session import init_db
    # Simulate legacy users table and verify old IDs/passwords survive.
    uid, old_hash = world["viewer"].id, world["viewer"].hashed_password
    db.rollback()
    with engine.begin() as c:
        c.execute(text("ALTER TABLE users DROP COLUMN username CASCADE, DROP COLUMN source_account_id CASCADE, DROP COLUMN staff_id CASCADE"))
    init_db(engine);init_db(engine)
    with Session(engine) as session:
        user = session.get(User, uid)
        assert user.username == "viewer@test.local" and user.hashed_password == old_hash
        assert user.student_id == "HS001"


def test_invalid_hash_and_unique_username(client, db, world, auth, source_accounts):
    from sqlalchemy.exc import IntegrityError
    db.execute(text("UPDATE accounts SET password_hash='plain-text-not-a-hash' WHERE username='hs002'"))
    db.commit()
    response = client.post("/api/v1/admin/accounts/sync", headers=auth["admin"])
    assert response.status_code == 200
    assert response.json()["created"] == 2
    assert any(r["reason"] == "unsupported_password_hash" for r in response.json()["items"])
    assert db.scalar(select(User).where(User.username == "hs002")) is None
    db.add(User(username="QT0001", full_name="Duplicate", role=Role.VIEWER, hashed_password="-"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_provisioned_teacher_login_change_password_and_groups(client, world, auth, source_accounts):
    sync = client.post("/api/v1/admin/accounts/sync", headers=auth["admin"])
    assert sync.status_code == 200
    uid = next(item["user_id"] for item in sync.json()["items"] if item["username"] == "gv0001")
    login = client.post("/api/v1/auth/login", json={"username":"gv0001","password":"Test@123"})
    assert login.status_code == 200
    old_headers = {"Authorization":"Bearer " + login.json()["access_token"]}
    assert client.get("/api/v1/learners", headers=old_headers).status_code == 403
    assert client.post("/api/v1/auth/change-password", headers=old_headers,
        json={"current_password":"Test@123","password":"ChangedTeacher123!"}).status_code == 200
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401
    login = client.post("/api/v1/auth/login", json={"username":"GV0001","password":"ChangedTeacher123!"})
    assert login.status_code == 200
    headers = {"Authorization":"Bearer " + login.json()["access_token"]}
    assert client.get("/api/v1/learners", headers=headers).json()["total"] == 0
    assert client.put(f"/api/v1/admin/teacher-accounts/{uid}/groups", headers=auth["admin"],
        json={"group_ids":[world["group_a"].id]}).status_code == 200
    assert client.get("/api/v1/learners", headers=headers).json()["total"] == 2
    assert client.get("/api/v1/reports/learner/HS003", headers=headers).status_code == 403
    # Re-sync does not reset the new password or assigned groups.
    client.post("/api/v1/admin/accounts/sync", headers=auth["admin"])
    assert client.post("/api/v1/auth/login", json={"username":"gv0001","password":"Test@123"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers=headers).json()["group_ids"] == [world["group_a"].id]
